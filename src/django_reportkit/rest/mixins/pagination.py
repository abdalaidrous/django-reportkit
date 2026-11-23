from dataclasses import dataclass, replace

# Query parameters of DRF's pagination classes; they never reach a report's filters.
PAGINATION_PARAMS = ("page_query_param", "page_size_query_param", "limit_query_param", "offset_query_param", "cursor_query_param")


@dataclass(frozen=True)
class ReportPage:
    """
    The rows of one page, with its number, the page count and the row count (None where the pagination has none).
    """

    rows: list
    number: int | None
    pages: int | None
    count: int


class ReportPaginationMixin:
    """
    Page a report through the view's DRF pagination class (DEFAULT_PAGINATION_CLASS unless pagination_class is set):
    the report supplies its source (Report.get_page_source) and reads each row (Report.read_page_row); DRF slices the
    source and shapes the response, so PageNumberPagination and LimitOffsetPagination both work. Without a pagination
    class the report pages itself from ?page= and ?page_size=.
    """

    def get_report_params(self, report_class):
        """
        Leave the pagination parameters out of the report's filters.
        """
        params = super().get_report_params(report_class)
        ignored = self.pagination_params()
        if not ignored:
            return params
        return replace(params, data={key: value for key, value in params.data.items() if key not in ignored})

    def pagination_params(self):
        """
        Return the query parameters the pagination class reads.
        """
        paginator = getattr(self, "paginator", None)
        return {getattr(paginator, name) for name in PAGINATION_PARAMS if getattr(paginator, name, None)}

    def get_report_page(self, report):
        """
        Return the report's own page from ?page= and ?page_size= (a Django Page).
        """
        params = self.request.query_params
        return report.get_page(params.get("page"), params.get("page_size"))

    def paginate_report(self, report):
        """
        Return the requested page as a ReportPage.
        """
        if self.paginator is None:
            page = self.get_report_page(report)
            return ReportPage(list(page.object_list), page.number, page.paginator.num_pages, page.paginator.count)

        rows = [report.read_page_row(row) for row in self.paginate_queryset(report.get_page_source())]
        page = getattr(self.paginator, "page", None)
        if page is None:
            return ReportPage(rows, None, None, report.count())
        return ReportPage(rows, page.number, page.paginator.num_pages, page.paginator.count)
