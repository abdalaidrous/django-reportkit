# Changelog

All notable changes to django-reportkit. The format follows [Keep a Changelog](https://keepachangelog.com/), and
versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-22

### Added

- `ModelReport` and `Report`: reports over a queryset (or any rows) with columns, a filter form with `filter_lookups`,
  totals aggregated by the database over every filtered row, lazy rows (`values().iterator()`), and a `build()` hook
  to lay the report out with pyreportkit's `ReportBuilder`.
- Access rules: `login_required` (default `True`) and `permission_required`.
- HTML preview with filters, pagination and download links (`Report.urls()`).
- Exports to PDF, Excel (formatted and streamed data), Word and HTML; `ExportPolicy` streams small exports from a
  temporary file, runs large ones in the background and refuses oversized ones with a suggestion.
- Background jobs: `ReportJob` model, Sync, Thread and Celery backends, status page, downloads for the job's user,
  expiry and the `cleanup_report_files` command.
- Django REST Framework API: a registry (`@register`) and generic URLs by slug for the report list, JSON pages,
  one-page HTML documents (`X-Report-*` headers) and exports; per-report `Report.api_urls()`.
- Friendly error messages and JSON errors with stable codes; details go to the `django_reportkit` logger.

[0.1.0]: https://github.com/abdalaidrous/django-reportkit/releases/tag/v0.1.0
