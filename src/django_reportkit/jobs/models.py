import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ReportJob(models.Model):
    """
    A report exported in the background: what to build (report class, format, parameters), its progress, and the
    stored file until it expires.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting")
        RUNNING = "running", _("Generating")
        DONE = "done", _("Ready")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.CharField(_("report"), max_length=255)

    title = models.CharField(_("title"), max_length=255, blank=True)

    format = models.CharField(_("format"), max_length=20)

    params = models.JSONField(_("parameters"), default=dict)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="report_jobs")

    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.PENDING)

    rows = models.PositiveIntegerField(_("rows"), default=0)

    file = models.CharField(_("file"), max_length=500, blank=True)

    filename = models.CharField(_("file name"), max_length=255, blank=True)

    error = models.TextField(_("error"), blank=True)

    created_at = models.DateTimeField(_("created"), auto_now_add=True)

    started_at = models.DateTimeField(_("started"), null=True, blank=True)

    finished_at = models.DateTimeField(_("finished"), null=True, blank=True)

    expires_at = models.DateTimeField(_("expires"), null=True, blank=True)

    class Meta:
        app_label = "django_reportkit"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "expires_at"])]
        verbose_name = _("report job")
        verbose_name_plural = _("report jobs")

    def __str__(self):
        """
        Show the report title, format and status.
        """
        return f"{self.title or self.report} ({self.format}, {self.status})"

    @property
    def finished(self):
        """
        Return whether the job has stopped, successfully or not.
        """
        return self.status in (self.Status.DONE, self.Status.FAILED)

    @property
    def expired(self):
        """
        Return whether the job has passed its expiration time.
        """
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def downloadable(self):
        """
        Return whether the job has a completed, unexpired export file.
        """
        return self.status == self.Status.DONE and bool(self.file) and not self.expired

    def can_access(self, user):
        """
        Return whether the authenticated user owns the job or has staff access.
        """
        return bool(user and user.is_authenticated and (user.pk == self.user_id or user.is_staff))