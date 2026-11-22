import threading

from django.db import transaction

from .base import JobBackend


class ThreadBackend(JobBackend):
    """
    Run the job in a thread of the web process after the transaction commits: no extra service needed, but a job is
    lost if the process restarts, so use Celery in production.
    """

    def submit(self, job_id):
        """
        Start a daemon thread for the job once the job row is committed.
        """
        from ..service import run_job  # Deferred: the service imports the backends' module.

        transaction.on_commit(lambda: threading.Thread(target=run_job, args=(job_id,), name=f"report-job-{job_id}", daemon=True).start())
