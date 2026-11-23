
from django import forms
from django.forms.utils import pretty_name
from django.urls import reverse
from django.utils.translation import get_language

from ..exports import FORMATS
from ..reports.params import ReportParams


GENERIC = "django_reportkit_api"
COLUMN_FIELDS = ("key", "title", "subtitle", "format", "decimals", "currency", "date_format", "align")
CHOICE_TYPES = ("choice", "multi_select")

FILTER_TYPES = (
    (forms.DateTimeField, "datetime"),
    (forms.DateField, "date"),
    (forms.UUIDField, "uuid"),
    (forms.IntegerField, "integer"),
    (forms.BooleanField, "boolean"),
    (forms.MultipleChoiceField, "multi_select"),
    (forms.ChoiceField, "choice"),
)


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
    return generic_url(request, route, report=report_class.get_slug(), **kwargs)


def custom_report_url(report_class, request, route, **kwargs):
    """
    Resolve a report URL through its dedicated API routes.
    """
    prefix = ":".join(current_namespaces(request))
    name = f"{report_class.get_slug()}-api-{route}"
    namespace = f"{prefix}:{name}" if prefix else name
    return request.build_absolute_uri(reverse(namespace, kwargs=kwargs))


def downloads_data(report, request):
    """
    Serialize available export URLs with the current filters.
    """
    suffix = query_suffix(report.params.urlencode())
    return {name: report_url(type(report), request, "export", export_format=name) + suffix for name in available_formats(report.formats)}


def query_suffix(query):
    """
    Build a URL query suffix when parameters are available.
    """
    return f"?{query}" if query else ""


def report_data(report_class, request):
    """
    Serialize a registered report for the generic viewer.
    """
    report = report_class(ReportParams(language=get_language() or "en"))
    slug = report_class.get_slug()

    return {
        "slug": slug,
        "title": report.get_title(),
        "formats": available_formats(report_class.formats),
        "filters": filters_data(report_class),
        "preview_url": generic_url(request, "preview", report=slug),
        "html_url": generic_url(request, "html", report=slug),
    }


def filters_data(report_class):
    """
    Describe the report's filter form fields (name, type, label, required, choices) for clients that build the form.
    """
    if report_class.filter_form is None:
        return []
    return [filter_data(name, field) for name, field in report_class.filter_form().fields.items()]


def filter_data(name, field):
    """
    Describe one filter form field.
    """
    kind = next((kind for field_class, kind in FILTER_TYPES if isinstance(field, field_class)), "string")
    data = {"name": name, "type": kind, "label": str(field.label or pretty_name(name)), "required": field.required}

    if kind in CHOICE_TYPES:
        data["choices"] = [str(value) for value, _ in field.choices if value not in ("", None)]

    return data


def available_formats(formats):
    """
    Return supported export formats.
    """
    supported = set(FORMATS)
    return [name for name in formats if name in supported]


def generic_url(request, route, **kwargs):
    """
    Build an absolute URL for a generic API route.
    """
    url = reverse(f"{generic_namespace(request)}:{route}", kwargs=kwargs)
    return request.build_absolute_uri(url)


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
