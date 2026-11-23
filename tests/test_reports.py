import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from django_reportkit import ReportParams
from django_reportkit.errors import ExportTooLargeError, ReportFilterError
from django_reportkit.jobs.models import ReportJob
from django_reportkit.jobs.storage import job_storage
from tests.reportapp.models import Account, Movement
from tests.reportapp.reports import MovementReport

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(client, django_user_model):
    """
    A client logged in as a regular user: reports require a login by default.
    """
    client.force_login(django_user_model.objects.create_user("reader"))
    return client


@pytest.fixture
def movements():
    """
    Five movements over two accounts, 1,500.00 in total.
    """
    cash, bank = Account.objects.create(name="الصندوق"), Account.objects.create(name="البنك")
    amounts = [Decimal("100.00"), Decimal("200.00"), Decimal("300.00"), Decimal("400.00"), Decimal("500.00")]
    for index, amount in enumerate(amounts):
        Movement.objects.create(voucher=f"{index + 1:06d}", date=date(2026, 11, 10 + index), account=cash if index % 2 else bank, amount=amount)


def report(**data):
    """
    Build the movement report with filter values.
    """
    return MovementReport(ReportParams(data={key: [value] for key, value in data.items()}, language="ar"))


class TestModelReport:

    def test_rows_are_lazy_and_can_be_read_again(self, movements, django_assert_num_queries):
        rows = report().get_rows()
        with django_assert_num_queries(1):
            first = list(rows)
        assert [row["voucher"] for row in first] == ["000001", "000002", "000003", "000004", "000005"]
        assert first[0]["account__name"] == "البنك"
        assert len(list(rows)) == 5

    def test_totals_cover_every_filtered_row_not_one_page(self, movements):
        assert report().get_totals() == {"amount": Decimal("1500.00")}
        assert report(date_from="2026-11-12").get_totals() == {"amount": Decimal("1200.00")}
        assert report(account="الصندوق").count() == 2

    def test_page_rows_with_full_totals(self, movements):
        page = report().get_page(2)
        assert [row["voucher"] for row in page.object_list] == ["000003", "000004"]
        assert page.paginator.num_pages == 3

    def test_document_has_the_total_row(self, movements):
        table = report().document().children[0].children[0]
        assert table.footer.kind == "total"
        assert table.footer.values == {"voucher": "Total", "amount": Decimal("1500.00")}

    def test_invalid_filters_raise(self, movements):
        with pytest.raises(ReportFilterError):
            report(date_from="not a date").count()

    def test_has_permission_applies_login_required(self):
        from django.contrib.auth.models import AnonymousUser

        from tests.reportapp.reports import PublicMovementReport

        assert not MovementReport.has_permission(AnonymousUser())
        assert PublicMovementReport.has_permission(AnonymousUser())
        assert MovementReport.has_permission(User(username="x"))

    def test_params_round_trip_through_json(self):
        params = ReportParams(data={"account": ["الصندوق"]}, user_id=3, language="ar")
        assert ReportParams.from_json(params.to_json()) == params
        assert params.direction == "rtl" and ReportParams(language="en-us").direction == "ltr"


class TestPreview:

    def test_preview_shows_one_page_and_download_links(self, client, movements):
        response = client.get(reverse("movement-report-preview"), {"page": 2, "account": ""})
        assert response.status_code == 200
        document = response.context["document"]
        assert "000003" in document and "000001" not in document
        assert "1,500.00" in document  # The totals of every row, on page 2.
        assert any("/export/xlsx-data/" in url for _, url in response.context["downloads"])

    def test_invalid_filters_show_the_form_errors(self, client, movements):
        response = client.get(reverse("movement-report-preview"), {"date_from": "x"})
        assert response.status_code == 400
        assert response.context["form"].errors

    def test_login_is_required_by_default(self, movements):
        from django.test import Client

        response = Client().get(reverse("movement-report-preview"))
        assert response.status_code == 302 and response["Location"].startswith("/login/?next=")
        assert Client().get(reverse("public-movements-preview")).status_code == 200

    @override_settings(REPORTKIT={"DIRECT_LIMITS": {"html": 3}, "JOB_BACKEND": "django_reportkit.jobs.backends.SyncBackend"})
    def test_background_exports_need_a_login_even_on_public_reports(self, movements):
        from django.test import Client

        response = Client().get(reverse("public-movements-export", kwargs={"format": "html"}))
        assert response.status_code == 302 and response["Location"].startswith("/login/")
        assert not ReportJob.objects.exists()

    def test_permission_is_required(self, client, movements):
        assert client.get(reverse("staff-movements-preview")).status_code == 403
        user = User.objects.create_user("staff")
        user.user_permissions.add(Permission.objects.get(codename="view_movement"))
        client.force_login(user)
        assert client.get(reverse("staff-movements-preview")).status_code == 200


class TestExport:

    def download(self, response):
        """
        Read a streamed file response.
        """
        return b"".join(response.streaming_content)

    def test_direct_html_export_streams_a_file(self, client, movements):
        response = client.get(reverse("movement-report-export", kwargs={"format": "html"}), {"account": "البنك"})
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith('attachment; filename="movement-report.html"')
        content = self.download(response).decode("utf-8")
        assert "000001" in content and "000002" not in content and "900.00" in content

    def test_direct_excel_exports(self, client, movements):
        openpyxl = pytest.importorskip("openpyxl")
        for format in ("xlsx", "xlsx-data"):
            response = client.get(reverse("movement-report-export", kwargs={"format": format}))
            book = openpyxl.load_workbook(io.BytesIO(self.download(response)))
            assert book.worksheets[-1].max_row >= 6

    def test_direct_pdf_and_word_exports(self, client, movements):
        pytest.importorskip("docx")
        word = self.download(client.get(reverse("movement-report-export", kwargs={"format": "docx"})))
        assert word.startswith(b"PK")
        try:
            from reportkit.exporters.pdf.dependencies import load_weasyprint

            load_weasyprint()
        except ImportError:
            pytest.skip("WeasyPrint is not installed")
        assert self.download(client.get(reverse("movement-report-export", kwargs={"format": "pdf"}))).startswith(b"%PDF")

    def test_unknown_format_is_a_friendly_error(self, client, movements):
        response = client.get(reverse("movement-report-export", kwargs={"format": "csv"}))
        assert response.status_code == 400
        assert "Traceback" not in response.content.decode("utf-8")

    @override_settings(REPORTKIT={"MAX_ROWS": {"html": 3}, "JOB_BACKEND": "django_reportkit.jobs.backends.SyncBackend"})
    def test_too_large_is_refused_with_an_alternative(self, client, movements):
        response = client.get(reverse("movement-report-export", kwargs={"format": "html"}))
        assert response.status_code == 413
        assert response.context["message"]

    @override_settings(REPORTKIT={"DIRECT_LIMITS": {"html": 3}, "JOB_BACKEND": "django_reportkit.jobs.backends.SyncBackend"})
    def test_large_export_runs_as_a_job(self, client, movements, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):  # Jobs are submitted once their row is committed.
            response = client.get(reverse("movement-report-export", kwargs={"format": "html"}))
        job = ReportJob.objects.get()
        assert response.status_code == 302 and response["Location"] == reverse("django_reportkit:job", kwargs={"job_id": job.pk})
        assert job.status == ReportJob.Status.DONE and job.rows == 5 and job.expires_at > timezone.now()
        state = client.get(response["Location"], {"format": "json"}).json()
        assert state["finished"] and state["download_url"]
        content = self.download(client.get(state["download_url"])).decode("utf-8")
        assert "000005" in content
        assert client.get(response["Location"]).status_code == 200


class TestJobs:

    def job(self, **fields):
        """
        Create a job record.
        """
        return ReportJob.objects.create(report=MovementReport.get_key(), format="html", filename="m.html", **fields)

    def test_failed_job_keeps_a_friendly_message(self, movements):
        from django_reportkit.jobs.service import ReportJobs

        job = self.job(params=ReportParams(data={"date_from": ["bad"]}).to_json())
        ReportJobs.run(job.pk)
        job.refresh_from_db()
        assert job.status == ReportJob.Status.FAILED and job.error and "Traceback" not in job.error

    def test_jobs_belong_to_their_user(self, client):
        owner, other = User.objects.create_user("owner"), User.objects.create_user("other")
        job = self.job(user=owner)
        url = reverse("django_reportkit:job", kwargs={"job_id": job.pk})
        assert client.get(url).status_code == 404
        client.force_login(other)
        assert client.get(url).status_code == 404
        client.force_login(owner)
        assert client.get(url).status_code == 200

    def test_cleanup_deletes_expired_jobs_and_files(self):
        name = job_storage().save("reports/old.html", io.BytesIO(b"x"))
        self.job(status=ReportJob.Status.DONE, file=name, expires_at=timezone.now() - timedelta(minutes=1))
        keep = self.job(status=ReportJob.Status.DONE, expires_at=timezone.now() + timedelta(hours=1))
        call_command("cleanup_report_files", stdout=io.StringIO())
        assert list(ReportJob.objects.all()) == [keep] and not job_storage().exists(name)

    def test_policy_suggests_the_data_format(self):
        from django_reportkit.exports import FORMATS, ExportPolicy

        with override_settings(REPORTKIT={"MAX_ROWS": {"pdf": 10}}), pytest.raises(ExportTooLargeError) as raised:
            ExportPolicy.decide(FORMATS["pdf"], 11, MovementReport.formats)
        assert raised.value.alternative == "xlsx-data"


@override_settings(TIME_ZONE="Asia/Riyadh")
def test_aware_datetimes_become_naive_local_time():
    """
    Rows carry aware datetimes in the current time zone without tzinfo (Excel stores none); other values stay as they are.
    """
    from datetime import datetime, timezone as dt_timezone

    from django_reportkit.reports.model import local_datetime

    value = local_datetime(datetime(2026, 11, 13, 21, 47, 54, tzinfo=dt_timezone.utc))
    assert value == datetime(2026, 11, 14, 0, 47, 54) and value.tzinfo is None
    assert local_datetime(date(2026, 11, 13)) == date(2026, 11, 13)
    assert local_datetime("text") == "text"
