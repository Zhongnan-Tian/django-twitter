from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from newsfeeds.api.serializers import NewsFeedSerializer
from utils.paginations import EndlessPagination
from newsfeeds.services import NewsFeedService
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from gatekeeper.models import GateKeeper


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # can only see the newsfeed of current logged in user's.
        # self.request.user.newsfeed_set.all() works too, but not very straightforward
        return NewsFeed.objects.filter(user=self.request.user)

    @method_decorator(
        ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request):
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        page = self.paginator.paginate_cached_list(cached_newsfeeds, request)
        # the requested data is not in cache, need query db.
        if page is None:
            if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
                page = self.paginator.paginate_hbase(HBaseNewsFeed,
                                                     (request.user.id,),
                                                     request)
            else:
                queryset = NewsFeed.objects.filter(user=request.user)
                page = self.paginate_queryset(queryset)

        serializer = NewsFeedSerializer(
            page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)
