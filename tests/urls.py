from django.urls import include, path

from tests.reportapp.reports import MovementReport, StaffReport

urlpatterns = [
    path("reports/movements/", include(MovementReport.urls())),
    path("reports/staff/", include(StaffReport.urls())),
    path("reports/", include("django_reportkit.urls")),
]
