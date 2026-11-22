from django import forms

from django_reportkit import Column, Count, ModelReport, Sum

from .models import Movement


class MovementFilterForm(forms.Form):
    date_from = forms.DateField(required=False)
    account = forms.CharField(required=False)


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


class StaffReport(MovementReport):
    slug = "staff-movements"
    permission_required = "reportapp.view_movement"
