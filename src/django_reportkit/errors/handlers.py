import logging

from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme

from .exceptions import ReportError
from .messages import friendly_message, status_code

logger = logging.getLogger("django_reportkit")


def log_error(error, report=None):
    """
    Log an error: expected report errors as warnings, anything else with its traceback.
    """
    name = type(report).__name__ if report is not None else "report"
    if isinstance(error, ReportError):
        logger.warning("%s: %s", name, error)
    else:
        logger.exception("%s failed", name, exc_info=error)


def error_response(request, error, report=None):
    """
    Log the error and render the friendly error page with the matching status.
    """
    log_error(error, report)
    context = {"message": friendly_message(error), "report": report, "back_url": back_url(request)}
    return render(request, "django_reportkit/error.html", context, status=status_code(error))


def back_url(request):
    """
    Return the referring page when it belongs to this site, for the error page's back link.
    """
    referer = request.META.get("HTTP_REFERER")
    return referer if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()) else None
