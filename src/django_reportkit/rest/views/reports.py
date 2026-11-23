from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...reports.registry import ReportRegistry
from ..serializers import report_data
from .export import ReportExportMixin
from .html import ReportHtmlMixin
from .preview import ReportPreviewMixin


def reports_data(request):
    """
    Return the registered reports the request's user may open.
    """
    return [report_data(report_class, request) for report_class in ReportRegistry.all() if report_class.has_request_permission(request)]


class ReportListAPIView(APIView):
    """
    The registered reports the user may open.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the reports.
        """
        return Response(reports_data(request))


class ReportViewSet(ReportPreviewMixin, ReportHtmlMixin, ReportExportMixin, viewsets.GenericViewSet):
    """
    Every registered report, addressed by its slug, for a DRF router:

        router.register("reports", ReportViewSet, basename="report")

    list: the user's reports; retrieve: one page of rows; html: one page as HTML; export/<format>: the file, or a 202
    background job.
    """
    lookup_url_kwarg = "report"
    lookup_value_regex = r"[-\w]+"

    def get_permissions(self):
        """
        The list needs a login; a report applies its own access rules.
        """
        if self.action == "list":
            return [IsAuthenticated()]
        return super().get_permissions()

    def list(self, request):
        """
        Return the reports the user may open.
        """
        return Response(reports_data(request))

    def retrieve(self, request, report=None):
        """
        Return one page of the report's rows.
        """
        instance = self.get_report()
        return self.handle_report(instance, lambda: self.page_response(instance))

    @action(detail=True, methods=["get"])
    def html(self, request, report=None):
        """
        Return one page of the report as HTML.
        """
        instance = self.get_report()
        return self.handle_report(instance, lambda: self.html_response(instance))

    @action(detail=True, methods=["get"], url_path=r"export/(?P<export_format>[-\w]+)")
    def export(self, request, export_format=None, report=None):
        """
        Return the export file, or a background job.
        """
        instance = self.get_report()
        return self.handle_report(instance, lambda: self.export_response(instance, export_format))
