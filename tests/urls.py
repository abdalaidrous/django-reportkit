from django.urls import include, path

from tests.reportapp.reports import MovementReport, PublicMovementReport, StaffReport

urlpatterns = [
    path("reports/movements/", include(MovementReport.urls())),
    path("reports/staff/", include(StaffReport.urls())),
    path("reports/public/", include(PublicMovementReport.urls())),
    path("reports/", include("django_reportkit.urls")),
    path("api/reports/movements/", include(MovementReport.api_urls())),
    path("api/reports/public/", include(PublicMovementReport.api_urls())),
    path("api/reports/", include("django_reportkit.rest.urls")),
    path("outer/reports/", include(("tests.nested_urls", "outer"), namespace="outer")),
]
