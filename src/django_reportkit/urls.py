from django.urls import path

from .views.jobs import ReportJobDownloadView, ReportJobView

app_name = "django_reportkit"

urlpatterns = [
    path("jobs/<uuid:job_id>/", ReportJobView.as_view(), name="job"),
    path("jobs/<uuid:job_id>/download/", ReportJobDownloadView.as_view(), name="download"),
]
