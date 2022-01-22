from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from dateutil import parser
from django.conf import settings
from utils.time_constants import MAX_TIMESTAMP


class EndlessPagination(BasePagination):
    page_size = 20 if not settings.TESTING else 10

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    # TODO: When tweet is deleted, the deleted tweet can be cached somewhere else.
    # reverse_ordered_list could contain deleted ones,
    # skip the deleted ones by checking the cache.
    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            # parse to timestamp in ISO
            created_at__gt = parser.isoparse(
                request.query_params['created_at__gt'])
            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = parser.isoparse(
                request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # not found any objects which meet the criteria
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

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
            # created_at__lt is used for loading next page.
            # Find page_size + 1 records whose created_at < created_at__lt, order by reversed created_at.
            # For example, records are [...10, 9, 8, 7 .. 1]. Current page ends with 10.
            # If created_at__lt=10, page_size = 2
            # then we should return [9, 8, 7].
            # We load one more record in order to check whether there is next page
            # to avoid empty loading.
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def paginate_hbase(self, hb_model, row_key_prefix, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            start = (*row_key_prefix, created_at__gt)
            stop = (*row_key_prefix, MAX_TIMESTAMP)
            objects = hb_model.filter(start=start, stop=stop)
            if len(objects) and objects[0].created_at == int(created_at__gt):
                objects = objects[:0:-1]
            else:
                objects = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            #  hbase only supports <= instead of <,
            #  we need to put one more item to gurantee count of items for '<'  is
            #  page_size + 1
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix, None)
            objects = hb_model.filter(start=start, stop=stop,
                                      limit=self.page_size + 2, reverse=True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                objects = objects[:-1]
            else:
                self.has_next_page = False
            return objects

        prefix = (*row_key_prefix, None)
        objects = hb_model.filter(prefix=prefix, limit=self.page_size + 1,
                                  reverse=True)
        if len(objects) > self.page_size:
            self.has_next_page = True
            objects = objects[:-1]
        else:
            self.has_next_page = False
        return objects

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(cached_list, request)

        # when loading the latest data，paginated_list contains all the data,
        # just return
        if 'created_at__gt' in request.query_params:
            return paginated_list

        # when loading next page, has_next_page is true.
        # This means cached_list has enough data, just return.
        if self.has_next_page:
            return paginated_list

        # when loading next page, has_next_page is false,
        # and cached_list length is smaller than the max limit.
        # This means cached_list has all the data, just return.
        if len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT:
            return paginated_list

        # other scenarios means some data exists in db but not in cache.
        # need to query db.
        return None

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })
