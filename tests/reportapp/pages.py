from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class RecordsPagination(PageNumberPagination):
    """
    A project's own pagination format and parameters, for the tests of the DRF pagination path.
    """

    page_size = 2
    page_query_param = "p"
    page_size_query_param = "length"

    def get_paginated_response(self, data):
        """
        Answer in the project's format.
        """
        return Response({"page": self.page.number, "num_pages": self.page.paginator.num_pages, "recordsTotal": self.page.paginator.count, "data": data})
