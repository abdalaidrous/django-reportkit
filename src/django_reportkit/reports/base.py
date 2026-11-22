from ..conf import reportkit_settings
from .mixins import ReportAccessMixin, ReportDocumentMixin, ReportFilterMixin
from .params import ReportParams

FORMATS = ("pdf", "xlsx", "xlsx-data", "docx")


class Report(ReportAccessMixin, ReportFilterMixin, ReportDocumentMixin):
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
