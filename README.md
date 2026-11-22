# django-reportkit

Django reports on top of [pyreportkit](https://pypi.org/project/pyreportkit/): declare a report over a queryset, and
get a paginated HTML preview with filters, and downloads in PDF, Excel and Word that never block the request on large
data: small exports stream from a temporary file, large ones run in the background with a status page.

The data and the totals come from your database (the totals are aggregated over every filtered row, not one page);
pyreportkit only lays them out.

## Installation

```bash
pip install django-reportkit             # HTML preview and exports
pip install "django-reportkit[all]"      # + PDF, Excel, Word, Celery and Django REST Framework
pip install "django-reportkit[rest]"     # only the REST API
```

```python
INSTALLED_APPS = [..., "django_reportkit"]
```

```bash
python manage.py migrate django_reportkit
```

Requires Python 3.10+ and Django 4.2+.

## A report

```python
from django import forms
from django_reportkit import Column, ModelReport, Sum


class MovementFilterForm(forms.Form):
    date_from = forms.DateField(required=False)
    account = forms.CharField(required=False)


class MovementReport(ModelReport):
    title = "تقرير الحركة المالية"
    model = Movement
    filter_form = MovementFilterForm
    filter_lookups = {"date_from": "date__gte", "account": "account__name"}
    formats = ("pdf", "xlsx", "xlsx-data", "docx")
    paginate_by = 50
    permission_required = "ledger.view_movement"
    columns = (
        Column("voucher", "رقم السند", align="center"),
        Column("date", "التاريخ", format="date", date_format="%d/%m/%Y"),
        Column("account__name", "الحساب"),
        Column("amount", "المبلغ", format="currency", currency="﷼"),
    )
    totals = {"amount": Sum("amount")}

    def get_queryset(self):
        return super().get_queryset().filter(company=self.user.company).order_by("date")

    def build(self, builder, table):                      # optional: anything ReportBuilder offers
        return builder.header(hotel_identity(), repeat=True).add(table).qr_code(self.verification_url()).page_number()
```

```python
# urls.py
urlpatterns = [
    path("reports/movements/", include(MovementReport.urls())),   # preview and exports
    path("reports/", include("django_reportkit.urls")),           # background job status and downloads
]
```

| URL | Name | What it does |
|---|---|---|
| `reports/movements/` | `movement-report-preview` | One page of rows (`?page=`), the filter form and download links; totals of every row. |
| `reports/movements/export/<format>/` | `movement-report-export` | Downloads the filtered report, or starts a background job when it is large. |
| `reports/jobs/<id>/` | `django_reportkit:job` | The job's progress (`?format=json` for polling) and its download link. |
| `reports/jobs/<id>/download/` | `django_reportkit:download` | The stored file, for the job's user. |

Reports require a logged-in user: anonymous visitors are sent to `LOGIN_URL`. Set `login_required = False` for a
public report; its background exports still ask for a login, since a job belongs to the user who started it and only
that user (or staff) can follow and download it. `permission_required` adds Django permissions on top.

Columns read `values()` fields, so related fields (`account__name`) and annotations work, and rows stream with
`iterator()`. Columns take every pyreportkit `TableColumn` option. `Report` (without a model) is the base class for
reports whose rows come from somewhere else: implement `get_rows()`, `count()`, `get_page()` and optionally
`get_totals()`.

## REST API (Django REST Framework)

```python
urlpatterns = [
    path("api/reports/movements/", include(MovementReport.api_urls())),   # JSON preview and exports
    path("api/reports/", include("django_reportkit.rest.urls")),          # job status and downloads
]
```

Authentication is whatever `REST_FRAMEWORK` configures (session, token, JWT...); the report's `login_required` and
`permission_required` still apply. `api_urls(authentication_classes=[...], throttle_classes=[...])` passes options to
the views.

| Request | Response |
|---|---|
| `GET api/reports/movements/?page=2&date_from=2026-11-01` | `{"count", "page", "pages", "next", "previous", "columns", "results", "totals", "filters", "downloads"}`; totals cover every filtered row. Invalid filters: `400 {"detail", "code": "report_filter", "errors": {...}}`. |
| `GET api/reports/movements/export/xlsx/?...` | The file for a small report; `202 Accepted` with the job (and `Location: status_url`) for a large one; `413` with `"code": "export_too_large"` above `MAX_ROWS`. |
| `GET api/reports/jobs/<id>/` | `{"id", "status", "label", "finished", "error", "rows", "status_url", "download_url", ...}`: poll until `finished`. |
| `GET api/reports/jobs/<id>/download/` | The stored file, for the job's user. |

Every error is JSON with a friendly `detail` and a stable `code`; the traceback only goes to the logs.

## How exports are delivered

`ExportPolicy` decides from the row count:

- up to `DIRECT_LIMITS[format]`: written to a temporary file and streamed with `FileResponse`;
- up to `MAX_ROWS[format]`: a `ReportJob` runs in the background, the user goes to its status page, and the file is kept
  in storage for `JOB_TTL_HOURS`;
- above it: a friendly refusal that suggests "Excel (data)" (streamed, no row limit) or narrower filters.

Errors are logged with their traceback; users see a short message (filters, size, unavailable format, or a generic
failure), never a server error page.

## Settings

```python
REPORTKIT = {
    "PAGINATE_BY": 50,
    "DIRECT_LIMITS": {"pdf": 2000, "docx": 2000, "xlsx": 20000, "xlsx-data": 100000, "html": 5000},
    "MAX_ROWS": {"pdf": 50000, "docx": 50000, "xlsx": 100000, "xlsx-data": None, "html": 20000},
    "JOB_BACKEND": "django_reportkit.jobs.backends.ThreadBackend",   # or SyncBackend, CeleryBackend
    "JOB_STORAGE": "default",                                         # a key of settings.STORAGES
    "JOB_DIRECTORY": "reports",
    "JOB_TTL_HOURS": 24,
    "STATUS_POLL_SECONDS": 3,
    "PDF_WORKERS": 1,                                                 # pyreportkit parallel PDF layout
}
```

- `ThreadBackend` (default) needs nothing else but loses a job if the process restarts; use `CeleryBackend` in
  production (`pip install "django-reportkit[celery]"`, task `django_reportkit.run_report_job`).
- Run `python manage.py cleanup_report_files` periodically to delete expired files.
- Override the templates in `django_reportkit/` (`base.html`, `preview.html`, `job.html`, `error.html`) to match your site.

## Development

Tests run with pytest-django (`tests/` has a small app and settings):

```bash
pip install -e ".[all,test]"
python -m pytest
```
