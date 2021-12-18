from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from friendships.models import Friendship
from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendshipSerializerForCreate,
)
from django.contrib.auth.models import User


class FriendshipViewSet(viewsets.GenericViewSet):
    # POST /api/friendship/1/follow will make the logged in user follow user_id=1,
    # so queryset here should be User.objects.all().
    # This is because we set `detail=True` which will call get_object() by default.
    # Namely, queryset.filter(pk=1) to check whether the object exists.
    # If we use Friendship.objects.all, error 404 Not Found.
    queryset = User.objects.all()

    serializer_class = FriendshipSerializerForCreate

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request, pk):
        # /api/friendships/1/followers get user 1's followers
        friendships = Friendship.objects.filter(to_user_id=pk)
        serializer = FollowerSerializer(friendships, many=True)
        return Response(
            {'followers': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followings(self, request, pk):
        # /api/friendships/1/followings get user1's followings
        friendships = Friendship.objects.filter(from_user_id=pk)
        serializer = FollowingSerializer(friendships, many=True)
        return Response(
            {'followings': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request, pk):
        # /api/friendships/1/follow  follow user 1
        # If the follow action happens several times (follow button is clicked several times)
        # Be silent，No need to throw error.
        if Friendship.objects.filter(from_user=request.user, to_user=pk).exists():
            return Response({
                'success': True,
                'duplicate': True,
            }, status=status.HTTP_201_CREATED)

        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': pk,
        })

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        instance = serializer.save()
        return Response(
            FollowingSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk):
        # /api/friendships/1/unfollow  unfollow user 1
        # raise 404 if no user with id=pk
        unfollow_user = self.get_object()
        if request.user.id == unfollow_user.id:
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST)

        # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
        # Queryset delete returns two values: how many records are deleted totally,
        # how many records are deleted for every type.
        # Multiple types of date can be deleted, this is because foreign key sets cascade deletion by default.
        # For example, some attribute of A model is the foreign key of B model,
        # on_delete=models.CASCADE,
        # so when record B is getting deleted, record A will be deleted too。
        # CASCADE is dangerous，Use on_delete=models.SET_NULL instead.
        deleted, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=pk,
        ).delete()
        return Response({'success': True, 'deleted': deleted})

    # just in order to make the URL display on home page
    def list(self, request):
        return Response({'message': 'This is friendships home page'})