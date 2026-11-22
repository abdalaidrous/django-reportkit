import re
from functools import cached_property

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override
from reportkit.builders import ReportBuilder, TableBuilder
from reportkit.rendering.context import RenderingContext

from ..conf import reportkit_settings
from ..errors.exceptions import ReportFilterError
from .params import ReportParams

FORMATS = ("pdf", "xlsx", "xlsx-data", "docx")


class Report:
    """
    Abstract report: subclasses provide the rows (get_rows), the row count and optionally the totals; this class turns
    them into a pyreportkit Report through ReportBuilder. Instances are built from ReportParams, so the same report
    runs in a request or in a background job.
    """

    title = ""
    columns = ()
    filter_form = None
    formats = FORMATS
    paginate_by = None
    permission_required = None
    total_label = _("Total")
    page = {"margin": "12mm"}
    page_number = "{page} / {pages}"
    slug = None

    def __init__(self, params=None):
        """
        Bind the report to its parameters.
        """
        self.params = params if params is not None else ReportParams()

    @classmethod
    def get_slug(cls):
        """
        Return the name the report's URLs are named after: slug, or the class name in kebab case.
        """
        return cls.slug or re.sub(r"(?<!^)(?=[A-Z])", "-", cls.__name__).lower()

    @classmethod
    def get_key(cls):
        """
        Return the import path a background job uses to find the report class again.
        """
        return f"{cls.__module__}.{cls.__qualname__}"

    @classmethod
    def urls(cls):
        """
        Return the URL patterns of this report's preview and exports, for include().
        """
        from ..views.urls import report_urlpatterns  # Deferred: views import reports.

        return report_urlpatterns(cls)

    @classmethod
    def has_permission(cls, user):
        """
        Return whether the user may see the report; permission_required is a permission name or a list of them.
        """
        if cls.permission_required is None:
            return True
        required = (cls.permission_required,) if isinstance(cls.permission_required, str) else cls.permission_required
        return user.has_perms(required)

    @cached_property
    def user(self):
        """
        Return the user the report is built for, or None.
        """
        return get_user_model()._default_manager.filter(pk=self.params.user_id).first() if self.params.user_id else None

    @cached_property
    def form(self):
        """
        Return the bound filter form, or None when the report has no filters.
        """
        return self.filter_form(self.params.querydict() or None) if self.filter_form else None

    @cached_property
    def filters(self):
        """
        Return the cleaned filter values; an empty mapping when nothing is filled in.
        """
        if self.form is None or not self.form.is_bound:
            return {}
        if not self.form.is_valid():
            raise ReportFilterError(self.form.errors)
        return {name: value for name, value in self.form.cleaned_data.items() if value not in (None, "", [], ())}

    def get_title(self):
        """
        Return the report title.
        """
        return str(self.title)

    def get_columns(self):
        """
        Return the report columns.
        """
        return list(self.columns)

    def get_rows(self):
        """
        Return every row as mappings keyed by column field; a lazy iterable is best.
        """
        raise NotImplementedError

    def count(self):
        """
        Return the number of rows, used to choose how to export.
        """
        raise NotImplementedError

    def get_totals(self):
        """
        Return the prepared totals keyed by column field, or None; they cover every row, not one page.
        """
        return None

    def get_paginate_by(self):
        """
        Return the number of rows on one preview page.
        """
        return self.paginate_by or reportkit_settings.PAGINATE_BY

    def get_page(self, number):
        """
        Return a Django Page whose object_list holds the rows of one preview page.
        """
        raise NotImplementedError

    def context(self):
        """
        Return the pyreportkit rendering context for the report language.
        """
        return RenderingContext(language=self.params.language, direction=self.params.direction)

    def table(self, rows):
        """
        Build the report table over the rows, with the totals of every row.
        """
        return TableBuilder().columns(*(column.table_column() for column in self.get_columns())).rows(rows).totals(self.total_row()).build()

    def total_row(self):
        """
        Return the totals with their label in the first column, or None.
        """
        totals = self.get_totals()
        if not totals:
            return None
        return {self.get_columns()[0].field: str(self.total_label), **totals}

    def build(self, builder, table):
        """
        Lay the report out; override to add headers, footers, charts or QR codes around the table.
        """
        return builder.add(table).page_number(self.page_number)

    def document(self, rows=None):
        """
        Return the pyreportkit Report over the given rows (every row by default), in the report language.
        """
        with override(self.params.language):
            builder = ReportBuilder(self.get_title()).page(**self.page)
            return self.build(builder, self.table(rows if rows is not None else self.get_rows())).build()
