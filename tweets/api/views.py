from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from tweets.api.serializers import TweetSerializer, TweetCreateSerializer
from tweets.models import Tweet


class TweetViewSet(viewsets.GenericViewSet,
                   viewsets.mixins.CreateModelMixin,
                   viewsets.mixins.ListModelMixin):
    """
    API endpoint that allows users to create, list tweets
    """
    queryset = Tweet.objects.all()
    serializer_class = TweetCreateSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        overwrite list method，No need to list all tweets，Use user_id as the query filter.
        """
        if 'user_id' not in request.query_params:
            return Response('missing user_id', status=400)

        # select * from twitter_tweets
        # where user_id = xxx
        # order by created_at desc
        # This SQL query needs the composite index, user and created_at.
        # Not enough to have user index only.
        tweets = Tweet.objects.filter(
            user_id=request.query_params['user_id']
        ).order_by('-created_at')

        serializer = TweetSerializer(tweets, many=True)

        # usually JSON response is in format like hash table
        return Response({'tweets': serializer.data})

    def create(self, request, *args, **kwargs):
        """
        overrite create method, tweet.user is the current logged in user.
        """
        serializer = TweetCreateSerializer(
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
        return Response(TweetSerializer(tweet).data, status=201)
