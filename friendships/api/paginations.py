from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


# PageNumberPagination provides page_query_param = 'page'
# Client can control the page using this query parameter.
# http://api.example.org/accounts/?page=4&size=10
class FriendshipPagination(PageNumberPagination):
    # default page size
    page_size = 20
    # page_size_query_param is default to None, which means customalized page size is not allowed.
    # Set it to 'size', which means UI can pass size=10 as request parameter.
    # The size for mobile client and web client can be different.
    page_size_query_param = 'size'
    # the max value of customalized page size
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'total_results': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
        })
