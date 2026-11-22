from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from ..conf import reportkit_settings
from ..exports import FORMATS
from ..jobs.models import ReportJob
from ..jobs.storage import job_storage


class JobAccessMixin:
    """
    Load the job of the URL when the user may follow it; anything else is a 404, so job ids reveal nothing.
    """

    def get_job(self, job_id):
        """
        Return the job or raise Http404.
        """
        job = get_object_or_404(ReportJob, pk=job_id)
        if not job.can_access(self.request.user):
            raise Http404
        return job


class ReportJobView(JobAccessMixin, View):
    """
    Show a background export's progress; the page polls the JSON form of the same URL until the file is ready.
    """

    template_name = "django_reportkit/job.html"

    def get(self, request, job_id):
        """
        Render the status page, or its JSON when asked with ?format=json.
        """
        job = self.get_job(job_id)

        if request.GET.get("format") == "json":
            return JsonResponse(self.state(job))

        return self.render_page(request, job)

    def render_page(self, request, job):
        """
        Render the job status page with its current state and polling interval.
        """
        context = {"job": job, "state": self.state(job), "poll_seconds": reportkit_settings.STATUS_POLL_SECONDS}
        return render(request, self.template_name, context)

    @staticmethod
    def state(job):
        """
        Return the job state the page shows.
        """
        return {
            "status": job.status,
            "label": str(job.get_status_display()),
            "finished": job.finished,
            "error": job.error,
            "download_url": reverse("django_reportkit:download", kwargs={"job_id": job.pk}) if job.status == ReportJob.Status.DONE else None,
        }


class ReportJobDownloadView(JobAccessMixin, View):
    """
    Stream a finished background export from storage.
    """

    def get(self, request, job_id):
        """
        Return the stored file, or 404 when it is not ready or has expired.
        """
        job = self.get_job(job_id)
        storage = job_storage()

        self.validate_download(job, storage)
        return self.download(job, storage)

    @staticmethod
    def validate_download(job, storage):
        """
        Require a completed job with an existing export file.
        """
        if job.status != ReportJob.Status.DONE or not job.file or not storage.exists(job.file):
            raise Http404

    @staticmethod
    def download(job, storage):
        """
        Open the stored export and return it as a streaming attachment.
        """
        export_format = FORMATS.get(job.format)
        file = storage.open(job.file, "rb")

        try:
            return FileResponse(file, as_attachment=True, filename=job.filename, content_type=export_format.content_type if export_format else None)
        except Exception:
            file.close()
            raise
