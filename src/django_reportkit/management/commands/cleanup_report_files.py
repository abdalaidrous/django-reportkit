from django.core.management.base import BaseCommand

from ...jobs.cleanup import delete_expired_jobs


class Command(BaseCommand):
    """
    Delete expired background exports; run it periodically (cron or Celery beat).
    """

    help = "Delete expired report export files and their jobs."

    def handle(self, *args, **options):
        """
        Delete the expired jobs and report how many.
        """
        self.stdout.write(f"Deleted {delete_expired_jobs()} expired report jobs.")