from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from comments.models import Comment
from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
)
from utils.permissions import IsObjectOwner
from utils.decorators import required_params
from inbox.services import NotificationService
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit


class CommentViewSet(viewsets.GenericViewSet):
    """
    Implement list, create, update, destroy.
    No need to implement retrieve（query single comment）because we don't have
    the use case.
    """
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    filterset_fields = ('tweet_id',)

    def get_permissions(self):
        # Note AllowAny() / IsAuthenticated() to initiate instance
        # instead of AllowAny / IsAuthenticated which is just a class
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['destroy', 'update']:
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    @required_params(params=['tweet_id'])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='GET', block=True))
    def list(self, request, *args, **kwargs):
        print('=== comments list ===');
        queryset = self.get_queryset()
        # use prefetch_related to avoid users being loaded multiple times
        # along with every comment
        comments = self.filter_queryset(queryset)\
            .prefetch_related('user')\
            .order_by('created_at')
        serializer = CommentSerializer(
            comments,
            context={'request': request},
            many=True,
        )
        return Response(
            {'comments': serializer.data},
            status=status.HTTP_200_OK,
        )

    @method_decorator(
        ratelimit(key='user', rate='3/s', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        # Note 'data=' to indicate that the parameter is for 'data'
        # because the first parameter is `instance` by default.
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # save method will trigger create method in serializer.
        comment = serializer.save()
        NotificationService.send_comment_notification(comment)
        return Response(
            CommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @method_decorator(
        ratelimit(key='user', rate='3/s', method='POST', block=True))
    def update(self, request, *args, **kwargs):
        serializer = CommentSerializerForUpdate(
            # get_object is a DRF function，it will raise 404 error
            # if no object is found.
            instance=self.get_object(),
            data=request.data,
        )
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        # save method will trigger update method in serializer.
        # Whether to trigger create or update is determined by parameter instance.
        comment = serializer.save()
        return Response(
            CommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    @method_decorator(
        ratelimit(key='user', rate='5/s', method='POST', block=True))
    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        # DRF destroy returns status code = 204 no content by default,
        # we return 200 here.
        return Response({'success': True}, status=status.HTTP_200_OK)
