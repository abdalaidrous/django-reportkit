from django.urls import path

from .views import ReportExportAPIView, ReportJobAPIView, ReportJobDownloadAPIView, ReportPreviewAPIView

app_name = "django_reportkit_api"

urlpatterns = [
    path("jobs/<uuid:job_id>/", ReportJobAPIView.as_view(), name="job"),
    path("jobs/<uuid:job_id>/download/", ReportJobDownloadAPIView.as_view(), name="download"),
]


def report_api_urlpatterns(report_class, **view_options):
    """
    Return the API URLs of one report, named "<slug>-api-preview" and "<slug>-api-export"; view_options go to the
    views (for example authentication_classes or throttle_classes).
    """
    slug = report_class.get_slug()
    return [
        path("", ReportPreviewAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-preview"),
        path("export/<str:export_format>/", ReportExportAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-export"),
    ]
