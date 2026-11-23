import re

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from rest_framework.response import Response

from ..errors import ReportFilterError, friendly_message, log_error
from ..errors.messages import status_code


def error_response(error, report=None):
    """
    Log the error and return its friendly message as JSON: {"detail", "code"}, plus "errors" for invalid filters.
    """
    log_error(error, report)
    data = {"detail": friendly_message(error), "code": error_code(error)}
    if isinstance(error, ReportFilterError):
        data["errors"] = error.errors.get_json_data()
    return Response(data, status=status_code(error))


def error_code(error):
    """
    Return a stable machine-readable code from the error class name (ExportTooLargeError -> export_too_large).
    """
    if isinstance(error, ImportError):
        return "format_unavailable"
    if isinstance(error, PermissionDenied):
        return "permission_denied"
    if isinstance(error, (Http404, ObjectDoesNotExist)):
        return "not_found"
    name = re.sub(r"Error$", "", type(error).__name__) if type(error).__module__.startswith("django_reportkit") else "report_failed"
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
