from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from django.utils.translation import gettext as _

from .exceptions import ExportTooLargeError, ReportFilterError, UnknownFormatError


def friendly_message(error):
    """
    Return the message a user sees for an error; technical details stay in the logs.
    """
    if isinstance(error, ReportFilterError):
        return _("Please correct the report filters.")
    if isinstance(error, UnknownFormatError):
        return _("This report cannot be downloaded in that format.")
    if isinstance(error, ExportTooLargeError):
        message = _("The report has %(rows)s rows, more than %(limit)s allowed for this format.") % {"rows": f"{error.rows:,}", "limit": f"{error.limit:,}"}
        if error.alternative:
            message += " " + _("Download it as Excel (data) instead, or narrow the filters.")
        else:
            message += " " + _("Narrow the filters and try again.")
        return message
    if isinstance(error, ImportError):
        return _("This format is not available on the server right now.")
    if isinstance(error, PermissionDenied):
        return str(error) or _("You do not have permission to view this report.")
    if isinstance(error, (Http404, ObjectDoesNotExist)):
        return _("The requested report data was not found.")
    return _("The report could not be created. Please try again later.")


def status_code(error):
    """
    Return the HTTP status that matches the error.
    """
    if isinstance(error, (ReportFilterError, UnknownFormatError)):
        return 400
    if isinstance(error, ExportTooLargeError):
        return 413
    if isinstance(error, ImportError):
        return 503
    if isinstance(error, PermissionDenied):
        return 403
    if isinstance(error, (Http404, ObjectDoesNotExist)):
        return 404
    return 500
