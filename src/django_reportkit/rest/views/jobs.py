from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...exports import FORMATS
from ...jobs.models import ReportJob
from ...jobs.storage import job_storage
from ..serializers import job_data
from .export import file_response


class JobAPIMixin:
    """
    Resolve the user's background jobs and stream their files.
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

    def job_download(self, job):
        """
        Stream the job's file once it is done and unexpired, or raise Http404.
        """
        if not is_downloadable(job) or not job_storage().exists(job.file):
            raise Http404

        export = FORMATS.get(job.format)
        try:
            file = job_storage().open(job.file, "rb")
        except (FileNotFoundError, OSError):
            raise Http404 from None

        return file_response(file, job.filename, export.content_type if export else None)


class ReportJobAPIView(JobAPIMixin, APIView):
    """
    A background job's status.
    """

    def get(self, request, job_id):
        """
        Return the job's status as JSON.
        """
        return Response(job_data(self.get_job(job_id), request))


class ReportJobDownloadAPIView(JobAPIMixin, APIView):
    """
    A finished background job's file.
    """

    def get(self, request, job_id):
        """
        Stream the file or raise Http404.
        """
        return self.job_download(self.get_job(job_id))


class ReportJobViewSet(JobAPIMixin, viewsets.GenericViewSet):
    """
    The user's background jobs for a DRF router: retrieve gives the status, download the finished file.

        router.register("reports/jobs", ReportJobViewSet, basename="report-job")
    """
    lookup_url_kwarg = "job_id"
    lookup_value_regex = r"[0-9a-f-]{36}"

    def retrieve(self, request, job_id=None):
        """
        Return the job's status.
        """
        return Response(job_data(self.get_job(job_id), request))

    @action(detail=True, methods=["get"])
    def download(self, request, job_id=None):
        """
        Stream the job's finished file.
        """
        return self.job_download(self.get_job(job_id))


def is_downloadable(job):
    """
    Whether the job has a finished, unexpired file.
    """
    return job.status == ReportJob.Status.DONE and bool(job.file) and (job.expires_at is None or job.expires_at > timezone.now())
