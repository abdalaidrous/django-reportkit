from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exports import Delivery, ExportPolicy, ExportRunner, FORMATS, get_format
from ..jobs.models import ReportJob
from ..jobs.service import ReportJobs
from ..jobs.storage import job_storage
from ..reports.params import ReportParams
from .errors import error_response
from .permissions import ReportPermission
from .serializers import job_data, page_data


class ReportAPIMixin:
    """
    Build the view's report from the API request; authentication comes from the project's DRF settings.
    """

    report_class = None
    permission_classes = [ReportPermission]

    def get_report_class(self):
        """
        Return the configured report class or raise a configuration error.
        """
        if self.report_class is None:
            raise ImproperlyConfigured(f"{type(self).__name__} must define report_class.")
        return self.report_class

    def get_report(self):
        """
        Return the report bound to the query parameters, the user and the language of the request.
        """
        return self.get_report_class()(ReportParams.from_request(self.request))


class ReportPreviewAPIView(ReportAPIMixin, APIView):
    """
    GET: one page of rows (?page=), the totals of every filtered row, the columns and the download links.
    """

    def get(self, request):
        """
        Return the requested page as JSON.
        """
        report = self.get_report()
        try:
            return Response(page_data(report, report.get_page(request.query_params.get("page")), request))
        except Exception as error:
            return error_response(error, report)


class ReportExportAPIView(ReportAPIMixin, APIView):
    """
    GET: the file of a small export, or 202 Accepted with the background job of a large one (Location: its status).
    """

    def get(self, request, export_format):
        """
        Export the report or start a background job for it.
        """
        report = self.get_report()
        try:
            export = get_format(report, export_format)
            rows = report.count()
            if ExportPolicy.decide(export, rows, report.formats) is Delivery.BACKGROUND:
                return self.start_background(request, report, export, rows)
            spool = ExportRunner.to_temporary_file(report, export)
        except NotAuthenticated:
            raise
        except Exception as error:
            return error_response(error, report)
        return FileResponse(spool, as_attachment=True, filename=export.filename(report.get_slug()), content_type=export.content_type)

    @staticmethod
    def start_background(request, report, export, rows):
        """
        Create the job for the authenticated user and answer 202 with its state.
        """
        if not request.user.is_authenticated:
            raise NotAuthenticated("A background export belongs to a user; authenticate first.")
        data = job_data(ReportJobs.start(report, export, rows), request)
        return Response(data, status=status.HTTP_202_ACCEPTED, headers={"Location": data["status_url"]})


class JobAPIMixin:
    """
    Load the job of the URL for its owner (or staff); anything else is a 404.
    """

    permission_classes = [IsAuthenticated]

    def get_job(self, job_id):
        """
        Return the job or raise Http404.
        """
        job = get_object_or_404(ReportJob, pk=job_id)
        if not job.can_access(self.request.user):
            raise Http404
        return job


class ReportJobAPIView(JobAPIMixin, APIView):
    """
    GET: the state of a background export; poll it until "finished" is true, then follow "download_url".
    """

    def get(self, request, job_id):
        """
        Return the job state as JSON.
        """
        return Response(job_data(self.get_job(job_id), request))


class ReportJobDownloadAPIView(JobAPIMixin, APIView):
    """
    GET: the file of a finished background export.
    """

    def get(self, request, job_id):
        """
        Stream the stored file, or 404 when it is not ready or has expired.
        """
        job = self.get_job(job_id)
        storage = job_storage()
        if job.status != ReportJob.Status.DONE or not job.file or not storage.exists(job.file):
            raise Http404
        export = FORMATS.get(job.format)
        return FileResponse(storage.open(job.file, "rb"), as_attachment=True, filename=job.filename, content_type=export.content_type if export else None)
