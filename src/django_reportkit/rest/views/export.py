from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ...exports import Delivery, ExportPolicy, ExportRunner, get_format
from ...jobs.service import ReportJobs
from ..mixins import ReportAPIMixin
from ..serializers import job_data


class ReportExportMixin(ReportAPIMixin):
    """
    Answer with a report's export: the file at once, or a background job for a large one.
    """

    def export_response(self, report, export_format):
        """
        Return the file, or 202 with the job.
        """
        export = get_format(report, export_format)
        report.filters
        rows = report.count()
        if ExportPolicy.decide(export, rows, report.formats) is Delivery.BACKGROUND:
            return self.start_background(report, export, rows)
        return self.download_export(report, export)

    def start_background(self, report, export, rows):
        """
        Create a background job and return its status URL; a job belongs to a user, so it needs a login.
        """
        if not self.request.user.is_authenticated:
            raise NotAuthenticated("Authentication is required for background exports.")

        job = ReportJobs.start(report, export, rows)
        data = job_data(job, self.request)
        return Response(data, status=status.HTTP_202_ACCEPTED, headers={"Location": data["status_url"]})

    @staticmethod
    def download_export(report, export):
        """
        Generate and stream the export.
        """
        spool = ExportRunner.to_temporary_file(report, export)
        return file_response(spool, export.filename(report.get_slug()), export.content_type)


class ReportExportAPIView(ReportExportMixin, GenericAPIView):
    """
    A report's export.
    """

    def get(self, request, export_format, **kwargs):
        """
        Return the file or the job.
        """
        report = self.get_report()
        return self.handle_report(report, lambda: self.export_response(report, export_format))


def file_response(file, filename, content_type):
    """
    Stream a file as a download, closing it if the response cannot be built.
    """
    try:
        return FileResponse(file, as_attachment=True, filename=filename, content_type=content_type)
    except Exception:
        file.close()
        raise
