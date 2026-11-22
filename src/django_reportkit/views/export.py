from django.http import FileResponse
from django.shortcuts import redirect
from django.views import View

from ..errors import error_response
from ..exports import Delivery, ExportPolicy, ExportRunner, get_format
from ..jobs.service import ReportJobs
from .mixins import ReportViewMixin


class ReportExportView(ReportViewMixin, View):
    """
    Download the report in one format: small reports are written to a temporary file and streamed from disk, large ones
    become a background job and the user is sent to its status page; errors become a friendly page.
    """

    def get(self, request, format):
        """
        Export the report or start a background job for it.
        """
        report = self.get_report()

        try:
            export_format = get_format(report, format)
            rows = report.count()
            return self.export(report, export_format, rows)
        except Exception as error:
            return error_response(request, error, report)

    def export(self, report, export_format, rows):
        """
        Select background processing or direct download according to the export policy.
        """
        delivery = ExportPolicy.decide(export_format, rows, report.formats)

        if delivery is Delivery.BACKGROUND:
            if not self.request.user.is_authenticated:
                return self.handle_no_permission()  # A background job belongs to a user; log in first.
            return self.start_background(report, export_format, rows)

        return self.download(report, export_format)

    @staticmethod
    def start_background(report, export_format, rows):
        """
        Create a background export job and redirect to its status page.
        """
        job = ReportJobs.start(report, export_format, rows)
        return redirect("django_reportkit:job", job_id=job.pk)

    @staticmethod
    def download(report, export_format):
        """
        Export the report to a temporary file and return a streaming download response.
        """
        spool = ExportRunner.to_temporary_file(report, export_format)

        try:
            return FileResponse(spool, as_attachment=True, filename=export_format.filename(report.get_slug()), content_type=export_format.content_type)
        except Exception:
            spool.close()
            raise
