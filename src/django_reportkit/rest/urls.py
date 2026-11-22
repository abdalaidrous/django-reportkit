from django.urls import path

from .views import ReportExportAPIView, ReportHtmlAPIView, ReportJobAPIView, ReportJobDownloadAPIView, ReportListAPIView, ReportPreviewAPIView

app_name = "django_reportkit_api"

# One set of URLs for every report registered with @register, addressed by its slug; and the background jobs.
urlpatterns = [
    path("", ReportListAPIView.as_view(), name="reports"),
    path("jobs/<uuid:job_id>/", ReportJobAPIView.as_view(), name="job"),
    path("jobs/<uuid:job_id>/download/", ReportJobDownloadAPIView.as_view(), name="download"),
    path("<slug:report>/", ReportPreviewAPIView.as_view(), name="preview"),
    path("<slug:report>/html/", ReportHtmlAPIView.as_view(), name="html"),
    path("<slug:report>/export/<str:export_format>/", ReportExportAPIView.as_view(), name="export"),
]


def report_api_urlpatterns(report_class, **view_options):
    """
    Return the API URLs of one report, named "<slug>-api-preview", "<slug>-api-html" and "<slug>-api-export";
    view_options go to the views (for example authentication_classes or throttle_classes).
    """
    slug = report_class.get_slug()
    return [
        path("", ReportPreviewAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-preview"),
        path("html/", ReportHtmlAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-html"),
        path("export/<str:export_format>/", ReportExportAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-export"),
    ]
