from rest_framework import viewsets, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from newsfeeds.models import NewsFeed
from newsfeeds.api.serializers import NewsFeedSerializer
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # can only see the newsfeed of current logged in user's.
        # self.request.user.newsfeed_set.all() works too, but not very straightforward
        return NewsFeed.objects.filter(user=self.request.user)

    def list(self, request):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = NewsFeedSerializer(
            queryset,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)
