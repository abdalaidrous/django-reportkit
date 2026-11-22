from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from ..reports.params import ReportParams


class ReportViewMixin:
    """
    Build the view's report from the request and check that the user may see it.
    """

    report_class = None

    def get_report(self):
        """
        Return the report bound to the request parameters, or deny access.
        """
        report_class = self.get_report_class()
        self.check_permission(report_class)
        return report_class(ReportParams.from_request(self.request))

    def get_report_class(self):
        """
        Return the configured report class or raise a configuration error.
        """
        if self.report_class is None:
            raise ImproperlyConfigured(f"{self.__class__.__name__} must define report_class.")
        return self.report_class

    def check_permission(self, report_class):
        """
        Deny access when the user lacks permission to view the report.
        """
        if not report_class.has_permission(self.request.user):
            raise PermissionDenied