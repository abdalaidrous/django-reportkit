from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404, HttpResponse
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
from ..reports.registry import ReportRegistry
from .errors import error_response
from .permissions import ReportPermission
from .serializers import job_data, page_data, report_data


class ReportListAPIView(APIView):
    """
    List registered reports accessible to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the reports visible to the user.
        """
        reports = (report_data(report_class, request) for report_class in ReportRegistry.all() if report_class.has_request_permission(request))
        return Response(list(reports))


class ReportAPIMixin:
    """
    Resolve and initialize reports from API requests.
    """

    report_class = None
    permission_classes = [ReportPermission]

    def get_report_class(self):
        """
        Resolve the configured or registered report class.
        """
        if self.report_class is not None:
            return self.report_class

        if "report" not in self.kwargs:
            raise ImproperlyConfigured(f"{type(self).__name__} needs report_class or a <report> URL argument.")

        report_class = ReportRegistry.get(self.kwargs["report"])

        if report_class is None:
            raise Http404

        return report_class

    def get_report(self):
        """
        Initialize the report with request parameters.
        """
        report_class = self.get_report_class()
        return report_class(report_class.build_params(self.request))


class ReportPreviewAPIView(ReportAPIMixin, APIView):
    """
    Return paginated report data with prepared totals and metadata.
    """

    def get(self, request, **kwargs):
        """
        Return the requested report page as JSON.
        """
        report = self.get_report()

        try:
            page = report.get_page(request.query_params.get("page"))
            return Response(page_data(report, page, request))
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)


class ReportHtmlAPIView(ReportAPIMixin, APIView):
    """
    Render a report preview page as a complete HTML document.
    """

    def get(self, request, **kwargs):
        """
        Return the requested HTML page with pagination headers.
        """
        report = self.get_report()

        try:
            page = report.get_page(request.query_params.get("page"))
            return self.render_page(report, page)
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)

    @staticmethod
    def render_page(report, page):
        """
        Render the HTML response and attach pagination metadata.
        """
        response = HttpResponse(report.html(page.object_list), content_type="text/html; charset=utf-8")
        response["X-Report-Page"] = page.number
        response["X-Report-Pages"] = page.paginator.num_pages
        response["X-Report-Count"] = page.paginator.count
        return response


class ReportExportAPIView(ReportAPIMixin, APIView):
    """
    Export reports directly or schedule large exports in the background.
    """

    def get(self, request, export_format, **kwargs):
        """
        Select the export delivery strategy and execute it.
        """
        report = self.get_report()

        try:
            export, rows, delivery = self.prepare_export(report, export_format)

            if delivery is Delivery.BACKGROUND:
                return self.start_background(request, report, export, rows)

            return self.download(report, export)
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)

    @staticmethod
    def prepare_export(report, export_format):
        """
        Validate filters and determine the export delivery strategy.
        """
        export = get_format(report, export_format)
        report.filters
        rows = report.count()
        delivery = ExportPolicy.decide(export, rows, report.formats)
        return export, rows, delivery

    @staticmethod
    def start_background(request, report, export, rows):
        """
        Create a background export job and return its status URL.
        """
        if not request.user.is_authenticated:
            raise NotAuthenticated("Authentication is required for background exports.")

        job = ReportJobs.start(report, export, rows)
        data = job_data(job, request)
        return Response(data, status=status.HTTP_202_ACCEPTED, headers={"Location": data["status_url"]})

    @staticmethod
    def download(report, export):
        """
        Generate and stream the report export.
        """
        spool = ExportRunner.to_temporary_file(report, export)
        filename = export.filename(report.get_slug())
        return create_file_response(spool, filename, export.content_type)


class JobAPIMixin:
    """
    Resolve background jobs accessible to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get_job(self, job_id):
        """
        Return an accessible background job or raise Http404.
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
        Return the background job status as JSON.
        """
        return Response(job_data(self.get_job(job_id), request))


class ReportJobDownloadAPIView(JobAPIMixin, APIView):
    """
    Stream completed background exports that have not expired.
    """

    def get(self, request, job_id):
        """
        Download the completed export or raise Http404.
        """
        job = self.get_job(job_id)
        self.validate_download(job)
        return self.download(job)

    @classmethod
    def validate_download(cls, job):
        """
        Validate the job state, expiration, and stored file.
        """
        if not cls.is_downloadable(job):
            raise Http404

        if not job_storage().exists(job.file):
            raise Http404

    @staticmethod
    def is_downloadable(job):
        """
        Check whether the job has a completed and unexpired file.
        """
        return job.status == ReportJob.Status.DONE and bool(job.file) and (job.expires_at is None or job.expires_at > timezone.now())

    @staticmethod
    def download(job):
        """
        Open and stream the stored export file.
        """
        export = FORMATS.get(job.format)
        file = job_storage().open(job.file, "rb")
        content_type = export.content_type if export else None
        return create_file_response(file, job.filename, content_type)


def create_file_response(file, filename, content_type):
    """
    Create a streaming response and close the file on failure.
    """
    try:
        return FileResponse(file, as_attachment=True, filename=filename, content_type=content_type)
    except Exception:
        file.close()
        raise