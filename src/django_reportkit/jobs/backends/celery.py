from django.db import transaction

from .base import JobBackend


class CeleryBackend(JobBackend):
    """
    Send the job to a Celery worker after the transaction commits (pip install "django-reportkit[celery]").
    """

    def submit(self, job_id):
        """
        Queue the job's task.
        """
        from ..tasks import run_report_job

        transaction.on_commit(lambda: run_report_job.delay(job_id))
