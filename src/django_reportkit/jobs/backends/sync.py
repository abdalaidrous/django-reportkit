from .base import JobBackend


class SyncBackend(JobBackend):
    """
    Run the job at once, inside the request: for tests and development; the request waits for the file.
    """

    def submit(self, job_id):
        """
        Run the job now.
        """
        from ..service import ReportJobs  # Deferred: the service imports the backends' module.

        ReportJobs.run(job_id)
