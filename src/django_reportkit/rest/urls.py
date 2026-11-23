from django.urls import path

from .views import ReportExportAPIView, ReportHtmlAPIView, ReportJobViewSet, ReportPreviewAPIView, ReportViewSet

app_name = "django_reportkit_api"

# One set of URLs for every report registered with @register, addressed by its slug; and the background jobs.
urlpatterns = [
    path("", ReportViewSet.as_view({"get": "list"}), name="reports"),
    path("jobs/<uuid:job_id>/", ReportJobViewSet.as_view({"get": "retrieve"}), name="job"),
    path("jobs/<uuid:job_id>/download/", ReportJobViewSet.as_view({"get": "download"}), name="download"),
    path("<slug:report>/", ReportViewSet.as_view({"get": "retrieve"}), name="preview"),
    path("<slug:report>/html/", ReportViewSet.as_view({"get": "html"}), name="html"),
    path("<slug:report>/export/<str:export_format>/", ReportViewSet.as_view({"get": "export"}), name="export"),
]


def report_api_urlpatterns(report_class, **view_options):
    """
    Return the API URLs of one report, named "<slug>-api-preview", "<slug>-api-html" and "<slug>-api-export";
    view_options go to the views (for example authentication_classes, throttle_classes or pagination_class).
    """
    slug = report_class.get_slug()
    return [
        path("", ReportPreviewAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-preview"),
        path("html/", ReportHtmlAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-html"),
        path("export/<str:export_format>/", ReportExportAPIView.as_view(report_class=report_class, **view_options), name=f"{slug}-api-export"),
    ]
