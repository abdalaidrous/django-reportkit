from rest_framework.permissions import BasePermission


class ReportPermission(BasePermission):
    """
    Apply the report's own access rules: a login unless login_required is False, then permission_required.
    """

    def has_permission(self, request, view):
        """
        Return whether the request's user may use the view's report.
        """
        report_class = view.get_report_class()
        if report_class.login_required and not (request.user and request.user.is_authenticated):
            return False
        return report_class.has_permission(request.user)
