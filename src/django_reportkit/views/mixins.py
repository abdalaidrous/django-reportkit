from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import ImproperlyConfigured



class ReportViewMixin(AccessMixin):
    """
    Build the view's report from the request: anonymous users are sent to the login page (unless the report sets
    login_required = False), and users without the report's permissions are denied.
    """

    report_class = None

    def dispatch(self, request, *args, **kwargs):
        """
        Check access before the view runs.
        """
        report_class = self.get_report_class()
        if report_class.login_required and not request.user.is_authenticated:
            return self.handle_no_permission()
        if not report_class.has_request_permission(request):
            self.raise_exception = True
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_report(self):
        """
        Return the report bound to the request parameters.
        """
        report_class = self.get_report_class()
        return report_class(report_class.build_params(self.request))

    def get_report_class(self):
        """
        Return the configured report class or raise a configuration error.
        """
        if self.report_class is None:
            raise ImproperlyConfigured(f"{self.__class__.__name__} must define report_class.")
        return self.report_class
