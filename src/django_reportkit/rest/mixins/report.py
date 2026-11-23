from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from rest_framework.exceptions import APIException

from ...reports.registry import ReportRegistry
from ..errors import error_response
from ..permissions import ReportPermission


class ReportAPIMixin:
    """
    Resolve the view's report (its report_class, or the registered report named by the <report> URL argument), build
    it from the request and turn unexpected errors into JSON answers.
    """
    report_class = None
    permission_classes = [ReportPermission]

    def get_report_class(self):
        """
        Return the configured or registered report class.
        """
        if self.report_class is not None:
            return self.report_class

        slug = self.kwargs.get("report")
        if slug is None:
            raise ImproperlyConfigured(f"{type(self).__name__} needs report_class or a <report> URL argument.")

        report_class = ReportRegistry.get(slug)
        if report_class is None:
            raise Http404

        return report_class

    def get_report_params(self, report_class):
        """
        Return the report's parameters from the request.
        """
        return report_class.build_params(self.request)

    def get_report(self):
        """
        Initialize the report with the request's parameters.
        """
        report_class = self.get_report_class()
        return report_class(self.get_report_params(report_class))

    def handle_report(self, report, callback):
        """
        Run a report operation and convert unexpected errors into API responses.
        """
        try:
            return callback()
        except APIException:
            raise
        except Exception as error:
            return error_response(error, report)
