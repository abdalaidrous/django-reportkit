from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ..mixins import ReportAPIMixin, ReportPaginationMixin
from ..serializers import page_data, report_meta


class ReportPreviewMixin(ReportPaginationMixin, ReportAPIMixin):
    """
    Answer with one page of a report's rows as JSON.
    """

    def page_response(self, report):
        """
        Return the paginated response with the report's title, columns, totals, filters and downloads added; without
        a pagination class, django-reportkit's own page format.
        """
        if self.paginator is None:
            return Response(page_data(report, self.get_report_page(report), self.request))

        response = self.get_paginated_response(self.paginate_report(report).rows)
        response.data.update(report_meta(report, self.request))
        return response


class ReportPreviewAPIView(ReportPreviewMixin, GenericAPIView):
    """
    One page of a report's rows as JSON.
    """

    def get(self, request, **kwargs):
        """
        Return the requested page.
        """
        report = self.get_report()
        return self.handle_report(report, lambda: self.page_response(report))
