from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendshipSerializerForCreate,
)
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from gatekeeper.models import GateKeeper
from utils.paginations import EndlessPagination
from friendships.services import FriendshipService
from friendships.models import HBaseFollowing, HBaseFollower, Friendship

class FriendshipViewSet(viewsets.GenericViewSet):
    # POST /api/friendship/1/follow will make the logged in user follow user_id=1,
    # so queryset here should be User.objects.all().
    # This is because we set `detail=True` which will call get_object() by default.
    # Namely, queryset.filter(pk=1) to check whether the object exists.
    # If we use Friendship.objects.all, error 404 Not Found.
    queryset = User.objects.all()
    # Usually different views require different pagination rules.
    pagination_class = EndlessPagination

    serializer_class = FriendshipSerializerForCreate

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(
        ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        pk = int(pk)
        paginator = self.paginator
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(HBaseFollower, (pk,), request)
        else:
            friendships = Friendship.objects.filter(to_user_id=pk).order_by(
                '-created_at')
            page = paginator.paginate_queryset(friendships)

        serializer = FollowerSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(
        ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):
        pk = int(pk)
        paginator = self.paginator
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(HBaseFollowing, (pk,), request)
        else:
            friendships = Friendship.objects.filter(from_user_id=pk).order_by(
                '-created_at')
            page = paginator.paginate_queryset(friendships)

        serializer = FollowingSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
    def follow(self, request, pk):
        # /api/friendships/1/follow  follow user 1
        # check if user with id=pk exists
        to_follow_user = self.get_object();

        # If the follow action happens several times (follow button is clicked several times)
        # Be silent，No need to throw error.
        if FriendshipService.has_followed(request.user.id, to_follow_user.id):
            return Response({
                'success': True,
                'duplicate': True,
            }, status=status.HTTP_201_CREATED)

        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': to_follow_user.id,
        })

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        instance = serializer.save()
        return Response(
            FollowingSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
    def unfollow(self, request, pk):
        # /api/friendships/1/unfollow  unfollow user 1
        # raise 404 if no user with id=pk
        unfollow_user = self.get_object()
        if request.user.id == unfollow_user.id:
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted = FriendshipService.unfollow(request.user.id, int(pk))
        return Response({'success': True, 'deleted': deleted})

    # just in order to make the URL display on home page
    def list(self, request):
        return Response({'message': 'This is friendships home page'})