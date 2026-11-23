import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from django_reportkit.jobs.models import ReportJob

from .test_reports import movements  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
BACKGROUND = {"DIRECT_LIMITS": {"html": 1}, "JOB_BACKEND": "django_reportkit.jobs.backends.SyncBackend"}


@pytest.fixture
def api(django_user_model):
    """
    An API client authenticated as a regular user.
    """
    client = APIClient()
    client.force_authenticate(django_user_model.objects.create_user("api"))
    return client


def download(response):
    """
    Read a streamed file response.
    """
    return b"".join(response.streaming_content)


class TestPreviewApi:

    def test_page_with_full_totals_columns_and_downloads(self, api, movements):
        data = api.get(reverse("movement-report-api-preview"), {"page": 2}).json()
        assert (data["count"], data["page"], data["pages"], data["next"], data["previous"]) == (5, 2, 3, 3, 1)
        assert [row["voucher"] for row in data["results"]] == ["000003", "000004"]
        assert data["totals"]["amount"] in ("1500.00", 1500.0)
        assert [column["key"] for column in data["columns"]] == ["voucher", "date", "account__name", "amount"]
        assert data["downloads"]["xlsx-data"].startswith("http://testserver/api/reports/movements/export/xlsx-data/")

    def test_filters_narrow_rows_and_totals(self, api, movements):
        data = api.get(reverse("movement-report-api-preview"), {"account": "الصندوق"}).json()
        assert data["count"] == 2 and data["filters"] == {"account": ["الصندوق"]}

    def test_invalid_filters_return_the_field_errors(self, api, movements):
        response = api.get(reverse("movement-report-api-preview"), {"date_from": "x"})
        assert response.status_code == 400
        assert response.json()["code"] == "report_filter" and "date_from" in response.json()["errors"]

    def test_authentication_and_permissions(self, movements, django_user_model):
        assert APIClient().get(reverse("movement-report-api-preview")).status_code in (401, 403)
        assert APIClient().get(reverse("public-movements-api-preview")).status_code == 200


class TestHtmlApi:

    def test_one_page_as_html_with_full_totals(self, api, movements):
        response = api.get(reverse("movement-report-api-html"), {"page": 2})
        assert response.status_code == 200 and response["Content-Type"].startswith("text/html")
        html = response.content.decode("utf-8")
        assert html.startswith("<!DOCTYPE html>") and "000003" in html and "000004" in html and "000001" not in html
        assert "1,500.00" in html
        assert (response["X-Report-Page"], response["X-Report-Pages"], response["X-Report-Count"]) == ("2", "3", "5")

    def test_invalid_filters_are_json(self, api, movements):
        response = api.get(reverse("movement-report-api-html"), {"date_from": "x"})
        assert response.status_code == 400 and response.json()["code"] == "report_filter"


class TestExportApi:

    def test_small_export_is_the_file(self, api, movements):
        response = api.get(reverse("movement-report-api-export", kwargs={"export_format": "html"}))
        assert response.status_code == 200 and "000005" in download(response).decode("utf-8")

    def test_unknown_format_is_json(self, api, movements):
        response = api.get(reverse("movement-report-api-export", kwargs={"export_format": "csv"}))
        assert response.status_code == 400 and response.json()["code"] == "unknown_format"

    @override_settings(REPORTKIT={"MAX_ROWS": {"html": 3}})
    def test_too_large_is_413_json(self, api, movements):
        response = api.get(reverse("movement-report-api-export", kwargs={"export_format": "html"}))
        assert response.status_code == 413 and response.json()["code"] == "export_too_large"

    @override_settings(REPORTKIT=BACKGROUND)
    def test_large_export_is_a_job_to_poll_and_download(self, api, movements, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = api.get(reverse("movement-report-api-export", kwargs={"export_format": "html"}))
        assert response.status_code == 202
        job = response.json()
        assert response["Location"] == job["status_url"]
        state = api.get(job["status_url"]).json()
        assert state["finished"] and state["status"] == "done"
        assert "000005" in download(api.get(state["download_url"])).decode("utf-8")

    @override_settings(REPORTKIT=BACKGROUND)
    def test_background_export_needs_authentication(self, movements):
        response = APIClient().get(reverse("public-movements-api-export", kwargs={"export_format": "html"}))
        assert response.status_code in (401, 403) and not ReportJob.objects.exists()

    def test_jobs_belong_to_their_user(self, api, django_user_model):
        job = ReportJob.objects.create(report="x", format="html", user=django_user_model.objects.create_user("owner"))
        assert api.get(reverse("django_reportkit_api:job", kwargs={"job_id": job.pk})).status_code == 404


class TestGenericApi:
    """
    One set of URLs for every registered report, addressed by slug.
    """

    def test_list_shows_the_reports_the_user_may_open(self, api, movements):
        slugs = [report["slug"] for report in api.get(reverse("django_reportkit_api:reports")).json()]
        assert slugs == ["movement-report", "public-movements"]  # staff-movements needs a permission.

    def test_any_report_by_slug(self, api, movements):
        data = api.get(reverse("django_reportkit_api:preview", kwargs={"report": "movement-report"}), {"page": 2}).json()
        assert data["count"] == 5 and data["downloads"]["pdf"].startswith("http://testserver/api/reports/movement-report/export/pdf/")
        html = api.get(reverse("django_reportkit_api:html", kwargs={"report": "public-movements"}))
        assert html.status_code == 200 and html["X-Report-Count"] == "5"
        exported = api.get(reverse("django_reportkit_api:export", kwargs={"report": "movement-report", "export_format": "html"}))
        assert "000005" in download(exported).decode("utf-8")

    def test_unknown_or_forbidden_reports(self, api, movements):
        assert api.get(reverse("django_reportkit_api:preview", kwargs={"report": "nothing"})).status_code == 404
        assert api.get(reverse("django_reportkit_api:html", kwargs={"report": "staff-movements"})).status_code == 403


class TestRequestHooks:
    """
    request_context, has_request_permission and prepare_row.
    """

    def url(self, name, **kwargs):
        return reverse(f"django_reportkit_api:{name}", kwargs={"report": "account-movements", **kwargs})

    def test_request_permission_and_context_scope_the_report(self, api, movements):
        assert api.get(self.url("preview")).status_code == 403
        data = api.get(self.url("preview"), HTTP_X_ACCOUNT="الصندوق").json()
        assert data["count"] == 2 and [row["voucher"] for row in data["results"]] == ["V-000002", "V-000004"]
        assert "account-movements" not in [report["slug"] for report in api.get(reverse("django_reportkit_api:reports")).json()]

    def test_prepared_rows_reach_exports(self, api, movements):
        content = download(api.get(self.url("export", export_format="html"), HTTP_X_ACCOUNT="الصندوق")).decode("utf-8")
        assert "V-000002" in content and "V-000004" in content and "000001" not in content

    @override_settings(REPORTKIT=BACKGROUND)
    def test_background_jobs_keep_the_request_context(self, api, movements, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = api.get(self.url("export", export_format="html"), HTTP_X_ACCOUNT="البنك")
        job = ReportJob.objects.get()
        assert response.status_code == 202
        assert job.params["context"] == {"account": "البنك"}


class TestOuterNamespace:
    """
    The generic API included under a project namespace builds its links in that namespace.
    """

    @override_settings(REPORTKIT=BACKGROUND)
    def test_links_stay_under_the_outer_namespace(self, api, movements, django_capture_on_commit_callbacks):
        data = api.get(reverse("outer:django_reportkit_api:preview", kwargs={"report": "movement-report"})).json()
        assert data["downloads"]["pdf"].startswith("http://testserver/outer/reports/movement-report/export/pdf/")
        listed = api.get(reverse("outer:django_reportkit_api:reports")).json()
        assert listed[0]["html_url"].startswith("http://testserver/outer/reports/")
        with django_capture_on_commit_callbacks(execute=True):
            response = api.get(reverse("outer:django_reportkit_api:export", kwargs={"report": "movement-report", "export_format": "html"}))
        job = response.json()
        assert job["status_url"].startswith("http://testserver/outer/reports/jobs/")
        assert api.get(job["status_url"]).json()["download_url"].startswith("http://testserver/outer/reports/jobs/")


class TestClientPageSizeAndFilters:
    """
    ?page_size= within MAX_PAGE_SIZE, and the filter metadata of the report list.
    """

    def test_page_size_is_capped(self, api, movements):
        data = api.get(reverse("movement-report-api-preview"), {"page_size": 4}).json()
        assert (data["pages"], len(data["results"]), data["filters"]) == (2, 4, {})
        with override_settings(REPORTKIT={"MAX_PAGE_SIZE": 3}):
            assert len(api.get(reverse("movement-report-api-preview"), {"page_size": 50}).json()["results"]) == 3
        assert len(api.get(reverse("movement-report-api-preview"), {"page_size": "x"}).json()["results"]) == 2

    def test_report_list_describes_the_filters(self, api, movements):
        report = next(item for item in api.get(reverse("django_reportkit_api:reports")).json() if item["slug"] == "movement-report")
        assert report["filters"] == [
            {"name": "date_from", "type": "date", "label": "Date from", "required": False},
            {"name": "account", "type": "string", "label": "Account", "required": False},
        ]
