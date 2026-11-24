from abc import ABC, abstractmethod
from contextlib import contextmanager

from ..conf import reportkit_settings
from .mixins import ReportAccessMixin, ReportDocumentMixin, ReportFilterMixin
from .params import ReportParams


FORMATS = ("pdf", "xlsx", "xlsx-data", "docx")


class Report(ReportAccessMixin, ReportFilterMixin, ReportDocumentMixin, ABC):
    """
    Abstract report: subclasses provide prepared rows, their count and optionally totals; this class builds a
    ReportKit document for previews, downloads and background exports. Instances are built from ReportParams, so the
    same report runs in a request or in a background job.
    """

    formats = FORMATS
    paginate_by = None

    def __init__(self, params=None):
        """
        Bind the report to its parameters.
        """
        self.params = params if params is not None else ReportParams()
        # The preview page being drawn, as (number, pages), set only while drawing_page() renders it; None otherwise.
        self.preview_page = None

    @contextmanager
    def drawing_page(self, page=None, pages=None):
        """
        Draw within this block as preview page `page` of `pages` (no page: a whole document); the page never outlives
        the block, so a later rendering starts clean.
        """
        self.preview_page = (page, pages) if page is not None else None

        try:
            yield self
        finally:
            self.preview_page = None

    @property
    def is_last_page(self):
        """
        Return whether the document drawn ends the report: an export, or the last preview page. A report shows
        what closes it (a summary, totals over every row) on this page only.
        """
        if self.preview_page is None:
            return True

        number, pages = self.preview_page
        return number is None or pages is None or number >= pages

    @abstractmethod
    def get_rows(self):
        """
        Return every row as mappings keyed by column field; a lazy iterable is best.
        """

    @abstractmethod
    def count(self):
        """
        Return the number of rows, used to choose how to export.
        """

    @abstractmethod
    def get_page(self, number, page_size=None):
        """
        Return a Django Page whose object_list holds the rows of one preview page.
        """

    def get_page_source(self):
        """
        Return what a DRF pagination class pages: the prepared rows as a list (ModelReport pages its queryset).
        """
        return list(self.get_rows())

    def read_page_row(self, row):
        """
        Return a row of get_page_source() ready for display.
        """
        return row

    def get_paginate_by(self, page_size=None):
        """
        Return the number of rows on one page: the requested size up to MAX_PAGE_SIZE, or the report's default.
        """
        try:
            requested = int(page_size)
        except (TypeError, ValueError):
            requested = 0

        size = requested if requested > 0 else self.paginate_by or reportkit_settings.PAGINATE_BY
        return min(max(size, 1), reportkit_settings.MAX_PAGE_SIZE)