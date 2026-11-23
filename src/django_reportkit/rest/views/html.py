from django.http import HttpResponse
from rest_framework.generics import GenericAPIView

from ..mixins import ReportAPIMixin, ReportPaginationMixin


class ReportHtmlMixin(ReportPaginationMixin, ReportAPIMixin):
    """
    Answer with one page of a report as a complete HTML document.
    """

    def html_response(self, report):
        """
        Return the page's HTML with X-Report-Page, X-Report-Pages and X-Report-Count headers (those it knows).
        """
        page = self.paginate_report(report)
        response = HttpResponse(report.html(page.rows), content_type="text/html; charset=utf-8")
        for header, value in (("X-Report-Page", page.number), ("X-Report-Pages", page.pages), ("X-Report-Count", page.count)):
            if value is not None:
                response[header] = value
        return response


class ReportHtmlAPIView(ReportHtmlMixin, GenericAPIView):
    """
    One page of a report as HTML.
    """

    def get(self, request, **kwargs):
        """
        Return the requested HTML page.
        """
        report = self.get_report()
        return self.handle_report(report, lambda: self.html_response(report))
