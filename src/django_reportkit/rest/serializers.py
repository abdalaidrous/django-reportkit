from django.urls import reverse

from ..exports import FORMATS

COLUMN_FIELDS = ("key", "title", "subtitle", "format", "decimals", "currency", "date_format", "align")


def columns_data(report):
    """
    Describe the report columns, so a client can label and format the rows itself.
    """
    return [{name: getattr(column, name) for name in COLUMN_FIELDS} for column in (column.table_column() for column in report.get_columns())]


def downloads_data(report, request):
    """
    Return the absolute export URL of every format the report offers, with the current filters.
    """
    query = report.params.urlencode()
    suffix = f"?{query}" if query else ""
    return {name: request.build_absolute_uri(reverse(f"{report.get_slug()}-api-export", kwargs={"export_format": name}) + suffix) for name in report.formats if name in FORMATS}


def page_data(report, page, request):
    """
    Return one page of rows with the totals of every filtered row, the columns and the download links.
    """
    paginator = page.paginator
    return {
        "title": report.get_title(),
        "count": paginator.count,
        "page": page.number,
        "pages": paginator.num_pages,
        "next": page.next_page_number() if page.has_next() else None,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "columns": columns_data(report),
        "results": list(page.object_list),
        "totals": report.get_totals(),
        "filters": report.params.data,
        "downloads": downloads_data(report, request),
    }


def job_data(job, request):
    """
    Return the state of a background export, with its status and download URLs.
    """
    status_url = request.build_absolute_uri(reverse("django_reportkit_api:job", kwargs={"job_id": job.pk}))
    download_url = request.build_absolute_uri(reverse("django_reportkit_api:download", kwargs={"job_id": job.pk})) if job.status == job.Status.DONE else None
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
        "status_url": status_url,
        "download_url": download_url,
    }
