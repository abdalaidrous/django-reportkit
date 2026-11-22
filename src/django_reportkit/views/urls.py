from django.urls import path

from .export import ReportExportView
from .preview import ReportPreviewView


def report_urlpatterns(report_class):
    """
    Return the preview and export URLs of one report, named "<slug>-preview" and "<slug>-export".
    """
    slug = report_class.get_slug()
    return [
        path("", ReportPreviewView.as_view(report_class=report_class), name=f"{slug}-preview"),
        path("export/<str:format>/", ReportExportView.as_view(report_class=report_class), name=f"{slug}-export"),
    ]
