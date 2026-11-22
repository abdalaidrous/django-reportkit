from celery import shared_task

from .service import run_job


@shared_task(name="django_reportkit.run_report_job", ignore_result=True)
def run_report_job(job_id):
    """
    Run one background export job in a Celery worker.
    """
    run_job(job_id)
