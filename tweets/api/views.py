from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from tweets.api.serializers import (
    TweetSerializer,
    TweetSerializerForCreate,
    TweetSerializerForDetail,
)
from tweets.models import Tweet
from newsfeeds.services import NewsFeedService
from utils.decorators import required_params
from utils.paginations import EndlessPagination
from tweets.services import TweetService


class TweetViewSet(viewsets.GenericViewSet):
    """
    API endpoint that allows users to get, create, list tweets
    """
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate
    pagination_class = EndlessPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def retrieve(self, request, *args, **kwargs):
        serializer = TweetSerializerForDetail(
            self.get_object(),
            context={'request': request},
        )
        return Response(serializer.data)

    @required_params(params=['user_id'])
    def list(self, request, *args, **kwargs):
        # /api/tweets/?user_id=1
        """
        overwrite list method，No need to list all tweets，Use user_id as the query filter.
        """

        # select * from twitter_tweets
        # where user_id = xxx
        # order by created_at desc
        # This SQL query needs the composite index, user and created_at.
        # Not enough to have user index only.
        tweets = TweetService.get_cached_tweets(
            user_id=request.query_params['user_id'])

        tweets = self.paginate_queryset(tweets)

        serializer = TweetSerializer(
            tweets,
            context={'request': request},
            many=True,
        )

        return self.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        overrite create method, tweet.user is the current logged in user.
        """
        serializer = TweetSerializerForCreate(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': "Please check input",
                'errors': serializer.errors,
            }, status=400)
        tweet = serializer.save()
        NewsFeedService.fanout_to_followers(tweet)
        serializer = TweetSerializer(tweet, context={'request': request})
        return Response(serializer.data, status=201)
