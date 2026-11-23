"""
Celery task discovery: Celery imports "<app>.tasks" of every installed app, so expose the export job task here.
"""

from .jobs.tasks import run_report_job

__all__ = ["run_report_job"]
