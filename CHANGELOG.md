# Changelog

All notable changes to django-reportkit. The format follows [Keep a Changelog](https://keepachangelog.com/), and
versions follow [Semantic Versioning](https://semver.org/).

## [0.3.2] - 2026-11-24

### Added

- `Report.is_last_page`: while one preview page is drawn (`Report.drawing_page(page, pages)`, used by `html()`, the
  HTML API and the preview view), the report knows whether it is the last one, so it can draw what closes it (a
  summary over every row) there only. The page is set for that rendering only; exports are whole documents and
  always count as the last page.

## [0.3.1] - 2026-11-23

### Added

- The REST API is served by ViewSets (`ReportViewSet`, `ReportJobViewSet` in `django_reportkit.rest.views`),
  which a project can also register in its own router.
- Pages (JSON and HTML) go through DRF's pagination class (`DEFAULT_PAGINATION_CLASS` or `pagination_class`), so the
  API follows the project's page format and parameters, with `title`, `columns`, `totals`, `filters` and
  `downloads` added. Without a pagination class nothing changes (`?page=`, `?page_size=`).

### Fixed

- Background exports require a login again (an anonymous request to a public report could start a job owned by no
  one).

## [0.3.0] - 2026-11-23

### Added

- `?page_size=` on previews and the API, up to the new `MAX_PAGE_SIZE` setting (100 by default).
- The report list describes each report's filters (`name`, `type`, `label`, `required`, `choices`), so a client can
  build the filter form from the API.

### Fixed

- Aware datetimes are shown in the current time zone and passed on without tzinfo, so the Excel export no longer
  fails on them ("Excel cannot store time zones") and every format shows local time instead of UTC.

## [0.2.0] - 2026-11-22

### Added

- `Report.request_context(request)`: JSON-ready values a report needs from the request (for example a selected
  tenant or property id). They are kept in `ReportParams.context`, so background jobs build the same report.
- `Report.has_request_permission(request)`: access rules that depend on the request, used by the HTML views, the
  API and the report list (defaults to `has_permission(request.user)`).
- `ModelReport.prepare_row(row)`: turn stored codes into labels or combine fields, for every row in previews, the API
  and exports.
- `django_reportkit.tasks`, so Celery's task autodiscovery finds the export task.
- The REST API can be included under a project namespace (for example `include(("app.urls", "app"), namespace="reports")`): its links are built in the namespace that served the request.

### Changed

- `PermissionDenied` and `Http404` raised while building a report become friendly 403 and 404 responses
  (`permission_denied` and `not_found` codes in the API).

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

[0.3.2]: https://github.com/abdalaidrous/django-reportkit/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/abdalaidrous/django-reportkit/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/abdalaidrous/django-reportkit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/abdalaidrous/django-reportkit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/abdalaidrous/django-reportkit/releases/tag/v0.1.0
