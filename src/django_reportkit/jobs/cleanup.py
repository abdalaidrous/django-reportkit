import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import ReportJob
from .storage import delete_export


logger = logging.getLogger(__name__)
FAILED_JOB_RETENTION = timedelta(days=1)


def delete_expired_jobs(now=None):
    """
    Delete expired jobs with their files, and failed jobs older than a day; return how many were deleted.
    """
    now = now or timezone.now()
    count = 0

    for job in expired_jobs(now).iterator(chunk_size=200):
        if delete_job(job):
            count += 1

    return count


def expired_jobs(now):
    """
    Return completed expired jobs and failed jobs past their retention period.
    """
    failed_before = now - FAILED_JOB_RETENTION
    return ReportJob.objects.filter(Q(status=ReportJob.Status.DONE, expires_at__lte=now) | Q(status=ReportJob.Status.FAILED, finished_at__lte=failed_before)).order_by("pk")


def delete_job(job):
    """
    Delete a job and its stored export, retaining the record when cleanup fails.
    """
    try:
        if job.file:
            delete_export(job.file)
        job.delete()
        return True
    except Exception:
        logger.exception("Failed to delete report job %s", job.pk)
        return False
