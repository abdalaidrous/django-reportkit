from datetime import datetime
from functools import cached_property

from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.utils import timezone

from .base import Report
from .rows import QuerysetRows


class ModelReport(Report):
    """
    Report over a queryset: the filters narrow it, the rows stream from it with iterator(), and the totals are computed
    by the database over every filtered row (aggregate()), never over one page.

    Declare model or queryset, columns, totals (column field -> aggregate expression such as Sum("amount")) and
    optionally filter_form with filter_lookups (form field -> ORM lookup such as "date__gte").
    """

    model = None
    queryset = None
    totals = {}
    filter_lookups = {}
    chunk_size = 2000

    def get_queryset(self):
        """
        Return the base queryset; override to scope it to self.user or to add select_related() and annotations.
        """
        if self.queryset is not None:
            return self.queryset.all()
        if self.model is not None:
            return self.model._default_manager.all()
        raise ImproperlyConfigured(f"{type(self).__name__} needs a model, a queryset or a get_queryset() override.")

    def filter_queryset(self, queryset, filters):
        """
        Apply the cleaned filter values through filter_lookups (a field without a lookup filters by its own name).
        """
        return queryset.filter(**{self.filter_lookups.get(name, name): value for name, value in filters.items()})

    @cached_property
    def filtered_queryset(self):
        """
        Return the filtered queryset, built once per report.
        """
        return self.filter_queryset(self.get_queryset(), self.filters)

    def fields(self):
        """
        Return the values() fields the columns read.
        """
        return [column.field for column in self.get_columns()]

    def prepare_row(self, row):
        """
        Return a row ready for display; override to turn stored codes into labels or to combine fields. It receives
        the values() mapping and runs for every row, in previews, the API and exports.
        """
        return row

    def read_row(self, row):
        """
        Show aware datetimes in the current time zone as naive values (Excel and Word store no time zone), then
        prepare the row.
        """
        return self.prepare_row({key: local_datetime(value) for key, value in row.items()})

    def get_rows(self):
        """
        Return the rows read lazily, in chunks.
        """
        return QuerysetRows(self.filtered_queryset, self.fields(), self.chunk_size, self.read_row)

    def count(self):
        """
        Return the number of filtered rows.
        """
        return self.filtered_queryset.count()

    def get_totals(self):
        """
        Aggregate the totals over every filtered row.
        """
        return self.filtered_queryset.aggregate(**self.totals) if self.totals else None

    def get_page(self, number, page_size=None):
        """
        Return one preview page of rows; the paginator counts the filtered rows once.
        """
        page = Paginator(self.filtered_queryset.values(*self.fields()), self.get_paginate_by(page_size)).get_page(number)
        page.object_list = [self.read_row(row) for row in page.object_list]
        return page


def local_datetime(value):
    """
    Return an aware datetime in the current time zone without its tzinfo; any other value unchanged.
    """
    return timezone.localtime(value).replace(tzinfo=None) if isinstance(value, datetime) and timezone.is_aware(value) else value
