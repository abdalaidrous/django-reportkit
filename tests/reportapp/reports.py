from django import forms

from django_reportkit import Column, Count, ModelReport, Sum, register

from .models import Movement


class MovementFilterForm(forms.Form):
    date_from = forms.DateField(required=False)
    account = forms.CharField(required=False)


@register
class MovementReport(ModelReport):
    title = "تقرير الحركة المالية"
    model = Movement
    filter_form = MovementFilterForm
    filter_lookups = {"date_from": "date__gte", "account": "account__name"}
    formats = ("pdf", "xlsx", "xlsx-data", "docx", "html")
    paginate_by = 2
    columns = (
        Column("voucher", "رقم السند"),
        Column("date", "التاريخ", format="date", date_format="%d/%m/%Y"),
        Column("account__name", "الحساب"),
        Column("amount", "المبلغ", format="number", decimals=2, align="end"),
    )
    totals = {"amount": Sum("amount"), "voucher_count": Count("id")}

    def get_queryset(self):
        return super().get_queryset().select_related("account").order_by("date", "voucher")

    def get_totals(self):
        totals = super().get_totals()
        return {"amount": totals["amount"]}


@register
class PublicMovementReport(MovementReport):
    slug = "public-movements"
    login_required = False


@register
class StaffReport(MovementReport):
    slug = "staff-movements"
    permission_required = "reportapp.view_movement"


@register
class AccountScopedReport(MovementReport):
    """
    A report scoped by request state (the X-Account header), like a selected tenant, with prepared rows.
    """

    slug = "account-movements"

    @classmethod
    def has_request_permission(cls, request):
        return super().has_request_permission(request) and bool(request.headers.get("X-Account"))

    @classmethod
    def request_context(cls, request):
        return {"account": request.headers.get("X-Account")}

    def get_queryset(self):
        return super().get_queryset().filter(account__name=self.params.context["account"])

    def prepare_row(self, row):
        return {**row, "voucher": f"V-{row['voucher']}"}
