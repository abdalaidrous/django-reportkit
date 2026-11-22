from datetime import timedelta

from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from ..conf import reportkit_settings
from ..errors import friendly_message, log_error
from ..exports import ExportRunner, get_format
from ..reports.params import ReportParams
from .models import ReportJob
from .storage import job_storage, save_export


class ReportJobs:
    """
    Create background export jobs, hand them to the configured backend and run them.
    """

    @classmethod
    def start(cls, report, format, rows):
        """
        Record a job for the report and submit it once the current transaction commits.
        """
        with transaction.atomic():
            job = cls.create(report, format, rows)
            transaction.on_commit(lambda: cls.submit(job.pk))
        return job

    @staticmethod
    def create(report, format, rows):
        """
        Persist the report definition, export format, parameters and requesting user.
        """
        return ReportJob.objects.create(
            report=report.get_key(),
            title=report.get_title(),
            format=format.name,
            params=report.params.to_json(),
            user_id=report.params.user_id,
            rows=rows,
            filename=format.filename(report.get_slug()),
        )

    @classmethod
    def submit(cls, job_id):
        """
        Submit a committed job to the configured background backend.
        """
        cls.backend().submit(str(job_id))

    @staticmethod
    def backend():
        """
        Return the configured job backend.
        """
        return import_string(reportkit_settings.JOB_BACKEND)()

    @classmethod
    def run(cls, job_id):
        """
        Claim a pending job, generate its export and record the final result.
        """
        job = cls.claim(job_id)
        if job is None:
            return

        report = None
        name = None

        try:
            report = cls.build_report(job)
            format = get_format(report, job.format)
            name = cls.export(job, report, format)
            cls.complete(job, name)
        except Exception as error:
            log_error(error, report)
            cls.fail(job, error, name)

    @staticmethod
    def claim(job_id):
        """
        Atomically claim a pending job so only one worker can execute it.
        """
        now = timezone.now()
        claimed = ReportJob.objects.filter(pk=job_id, status=ReportJob.Status.PENDING).update(status=ReportJob.Status.RUNNING, started_at=now)

        if not claimed:
            return None

        return ReportJob.objects.get(pk=job_id)

    @staticmethod
    def build_report(job):
        """
        Reconstruct the report using its stored definition and parameters.
        """
        report_class = import_string(job.report)
        return report_class(ReportParams.from_json(job.params))

    @staticmethod
    def export(job, report, format):
        """
        Generate the report and save its output to the configured storage.
        """
        with ExportRunner.to_temporary_file(report, format) as spool:
            return save_export(job, spool)

    @classmethod
    def complete(cls, job, name):
        """
        Mark the job as completed and record its stored file and expiration time.
        """
        finished = timezone.now()
        expires = finished + timedelta(hours=reportkit_settings.JOB_TTL_HOURS)
        cls.mark(job, status=ReportJob.Status.DONE, file=name, finished_at=finished, expires_at=expires)

    @classmethod
    def fail(cls, job, error, name=None):
        """
        Mark the job as failed and remove any exported file left behind.
        """
        try:
            if name:
                job_storage().delete(name)
        finally:
            cls.mark(job, status=ReportJob.Status.FAILED, error=friendly_message(error), finished_at=timezone.now())

    @staticmethod
    def mark(job, **fields):
        """
        Save the supplied job fields.
        """
        for name, value in fields.items():
            setattr(job, name, value)
        job.save(update_fields=list(fields))


def run_job(job_id):
    """
    Run one job outside the request cycle, closing stale database connections around it.
    """
    close_old_connections()
    try:
        ReportJobs.run(job_id)
    finally:
        close_old_connections()
