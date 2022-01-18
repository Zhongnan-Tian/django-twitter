from rest_framework.pagination import BasePagination
from rest_framework.response import Response


class EndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__gt' in request.query_params:
            # created_at__gt is used for loading latest records.
            # We just load all the latest records, instead of doing pagination.
            # If there is too much data, return the top ones and tell client to reload,
            # like app is restarted.
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            # created_at__lt is used for loading the next page.
            # Find page_size + 1 records whose created_at < created_at__lt, order by reversed created_at.
            # For example, records are [...10, 9, 8, 7 .. 1]. Current page ends with 10.
            # If created_at__lt=10, page_size = 2
            # then we should return [9, 8, 7].
            # We return one more record in order to check whether there is next page
            # to avoid empty loading.
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })
