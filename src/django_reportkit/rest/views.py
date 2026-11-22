from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated
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
    Build the report from the API request using the configured report class and DRF permissions.
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
        Return the report bound to the request parameters and requesting user.
        """
        return self.get_report_class()(ReportParams.from_request(self.request))


class ReportPreviewAPIView(ReportAPIMixin, APIView):
    """
    Return one page of report rows, prepared totals, columns and available export links.
    """

    def get(self, request):
        """
        Return the requested preview page as JSON.
        """
        report = self.get_report()
        try:
            return Response(page_data(report, report.get_page(request.query_params.get("page")), request))
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)


class ReportExportAPIView(ReportAPIMixin, APIView):
    """
    Export small reports directly or return a background job for large reports.
    """

    def get(self, request, export_format):
        """
        Export the report or start a background job according to its export policy.
        """
        report = self.get_report()

        try:
            export = get_format(report, export_format)
            report.filters
            rows = report.count()
            delivery = ExportPolicy.decide(export, rows, report.formats)

            if delivery is Delivery.BACKGROUND:
                return self.start_background(request, report, export, rows)

            return self.download(report, export)
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)

    @staticmethod
    def start_background(request, report, export, rows):
        """
        Create a background export for the authenticated user and return its status URL.
        """
        if not request.user.is_authenticated:
            raise NotAuthenticated("Authentication is required for background exports.")

        data = job_data(ReportJobs.start(report, export, rows), request)
        return Response(data, status=status.HTTP_202_ACCEPTED, headers={"Location": data["status_url"]})

    @staticmethod
    def download(report, export):
        """
        Generate and stream the export while ensuring the temporary file is closed on failure.
        """
        spool = ExportRunner.to_temporary_file(report, export)

        try:
            return FileResponse(spool, as_attachment=True, filename=export.filename(report.get_slug()), content_type=export.content_type)
        except Exception:
            spool.close()
            raise


class JobAPIMixin:
    """
    Load background jobs accessible to the authenticated requesting user.
    """

    permission_classes = [IsAuthenticated]

    def get_job(self, job_id):
        """
        Return the requested job or raise Http404 when it is inaccessible.
        """
        job = get_object_or_404(ReportJob, pk=job_id)

        if not job.can_access(self.request.user):
            raise Http404

        return job


class ReportJobAPIView(JobAPIMixin, APIView):
    """
    Return the current status of a background export job.
    """

    def get(self, request, job_id):
        """
        Return the job state as JSON.
        """
        return Response(job_data(self.get_job(job_id), request))


class ReportJobDownloadAPIView(JobAPIMixin, APIView):
    """
    Stream completed background exports that have not expired.
    """

    def get(self, request, job_id):
        """
        Stream the stored file or raise Http404 when it is unavailable or expired.
        """
        job = self.get_job(job_id)

        if not self.is_downloadable(job):
            raise Http404

        storage = job_storage()

        if not storage.exists(job.file):
            raise Http404

        export = FORMATS.get(job.format)
        file = storage.open(job.file, "rb")

        try:
            return FileResponse(file, as_attachment=True, filename=job.filename, content_type=export.content_type if export else None)
        except Exception:
            file.close()
            raise

    @staticmethod
    def is_downloadable(job):
        """
        Return whether the job has a completed, unexpired export file.
        """
        return job.status == ReportJob.Status.DONE and bool(job.file) and (job.expires_at is None or job.expires_at > timezone.now())
