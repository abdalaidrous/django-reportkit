from django.urls import reverse
from django.utils.translation import get_language

from ..exports import FORMATS
from ..reports.params import ReportParams


GENERIC = "django_reportkit_api"
COLUMN_FIELDS = ("key", "title", "subtitle", "format", "decimals", "currency", "date_format", "align")


def columns_data(report):
    """
    Serialize report column definitions.
    """
    return [column_data(column.table_column()) for column in report.get_columns()]


def column_data(column):
    """
    Serialize a single table column.
    """
    return {name: getattr(column, name) for name in COLUMN_FIELDS}


def report_url(report_class, request, route, **kwargs):
    """
    Resolve the absolute URL for a report API route.
    """
    if GENERIC in current_namespaces(request):
        return generic_report_url(report_class, request, route, **kwargs)

    return custom_report_url(report_class, request, route, **kwargs)


def generic_report_url(report_class, request, route, **kwargs):
    """
    Resolve a report URL through the generic API namespace.
    """
    url = reverse(f"{generic_namespace(request)}:{route}", kwargs={"report": report_class.get_slug(), **kwargs})
    return request.build_absolute_uri(url)


def custom_report_url(report_class, request, route, **kwargs):
    """
    Resolve a report URL through its dedicated API routes.
    """
    prefix = "".join(f"{namespace}:" for namespace in current_namespaces(request))
    url = reverse(f"{prefix}{report_class.get_slug()}-api-{route}", kwargs=kwargs)
    return request.build_absolute_uri(url)


def downloads_data(report, request):
    """
    Serialize available export URLs with the current filters.
    """
    suffix = query_suffix(report.params.urlencode())
    return {name: report_url(type(report), request, "export", export_format=name) + suffix for name in report.formats if name in FORMATS}


def query_suffix(query):
    """
    Build a URL query suffix when parameters are available.
    """
    return f"?{query}" if query else ""


def report_data(report_class, request):
    """
    Serialize a registered report for the generic viewer.
    """
    return {
        "slug": report_class.get_slug(),
        "title": report_class(ReportParams(language=get_language() or "en")).get_title(),
        "formats": available_formats(report_class.formats),
        "preview_url": generic_url(request, "preview", report=report_class.get_slug()),
        "html_url": generic_url(request, "html", report=report_class.get_slug()),
    }


def available_formats(formats):
    """
    Return supported export formats.
    """
    return [name for name in formats if name in FORMATS]


def generic_url(request, route, **kwargs):
    """
    Build an absolute URL for a generic API route.
    """
    return request.build_absolute_uri(reverse(f"{generic_namespace(request)}:{route}", kwargs=kwargs))


def current_namespaces(request):
    """
    Return the namespaces of the URL that served the request, outermost first.
    """
    match = getattr(request, "resolver_match", None)
    return list(match.namespaces) if match is not None else []


def generic_namespace(request):
    """
    Return the full namespace of the generic API, including any outer namespace it is included under.
    """
    namespaces = current_namespaces(request)
    if GENERIC in namespaces:
        return ":".join(namespaces[:namespaces.index(GENERIC) + 1])
    return GENERIC


def page_data(report, page, request):
    """
    Serialize a report page with its prepared totals and export links.
    """
    return {
        "title": report.get_title(),
        **pagination_data(page),
        "columns": columns_data(report),
        "results": list(page.object_list),
        "totals": report.get_totals(),
        "filters": report.params.data,
        "downloads": downloads_data(report, request),
    }


def pagination_data(page):
    """
    Serialize pagination metadata.
    """
    return {
        "count": page.paginator.count,
        "page": page.number,
        "pages": page.paginator.num_pages,
        "next": page.next_page_number() if page.has_next() else None,
        "previous": page.previous_page_number() if page.has_previous() else None,
    }


def job_data(job, request):
    """
    Serialize a background export job with its status and download URLs.
    """
    return {
        "id": str(job.pk),
        "title": job.title,
        "format": job.format,
        "rows": job.rows,
        "status": job.status,
        "label": str(job.get_status_display()),
        "finished": job.finished,
        "error": job.error or None,
        "created_at": job.created_at,
        "expires_at": job.expires_at,
        "status_url": generic_url(request, "job", job_id=job.pk),
        "download_url": job_download_url(job, request),
    }


def job_download_url(job, request):
    """
    Return the download URL for a completed export job.
    """
    if job.status != job.Status.DONE:
        return None

    return generic_url(request, "download", job_id=job.pk)