from django.conf import settings
from django.core.cache import caches
from friendships.models import HBaseFollowing, HBaseFollower, Friendship
from twitter.cache import FOLLOWINGS_PATTERN
from gatekeeper.models import GateKeeper

import time

cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        # wrong approach 1
        # friendships = Friendship.objects.filter(to_user=user)
        # return [friendship.from_user for friendship in friendships]
        # This approach leads to N + 1 Queries.
        # One query: filter friendships
        # N queries: every friendship in the for loop queries from_user

        # wrong approach 2
        # friendships = Friendship.objects.filter(
        #     to_user=user
        # ).select_related('from_user')
        # return [friendship.from_user for friendship in friendships]
        # It joins friendship table and user table on attribute from_user
        # join operation is very slow in large scale web applications.

        # Correct approach 1: filter ids, then use IN Query.
        # friendships = Friendship.objects.filter(to_user=user)
        # follower_ids = [friendship.from_user_id for friendship in friendships]
        # followers = User.objects.filter(id__in=follower_ids)

        # Correct approach 2: use prefetch_related，It will execute two queries，
        # Same with the IN query above.
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]

    # TODO: cache followers list
    def get_follower_ids(cls, to_user_id):
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            friendships = Friendship.objects.filter(to_user_id=to_user_id)
        else:
            friendships = HBaseFollower.filter(prefix=(to_user_id, None))
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):
        # TODO: cache in redis
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            friendships = Friendship.objects.filter(from_user_id=from_user_id)
        else:
            friendships = HBaseFollowing.filter(prefix=(from_user_id, None))
        user_id_set = set([
            fs.to_user_id
            for fs in friendships
        ])
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        cache.delete(key)

    @classmethod
    def get_follow_instance(cls, from_user_id, to_user_id):
        followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        for follow in followings:
            if follow.to_user_id == to_user_id:
                return follow
        return None

    @classmethod
    def has_followed(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return True

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            return Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).exists()

        instance = cls.get_follow_instance(from_user_id, to_user_id)
        return instance is not None

    @classmethod
    def follow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return None

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # create data in mysql
            return Friendship.objects.create(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            )

        # create data in hbase
        now = int(time.time() * 1000000)
        HBaseFollower.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )
        return HBaseFollowing.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )

    @classmethod
    def unfollow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return 0

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
            # Queryset delete returns two values: how many records are deleted totally,
            # how many records are deleted for every type.
            # Multiple types of date can be deleted, this is because foreign key
            # sets cascade deletion by default.
            # For example, some attribute of A model is the foreign key of B model,
            # on_delete=models.CASCADE,
            # so when record B is getting deleted, record A will be deleted too。
            # CASCADE is dangerous，Use on_delete=models.SET_NULL instead.
            deleted, _ = Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).delete()
            return deleted

        instance = cls.get_follow_instance(from_user_id, to_user_id)
        if instance is None:
            return 0

        HBaseFollowing.delete(from_user_id=from_user_id,
                              created_at=instance.created_at)
        HBaseFollower.delete(to_user_id=to_user_id,
                             created_at=instance.created_at)
        return 1

    @classmethod
    def get_following_count(cls, from_user_id):
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            return Friendship.objects.filter(from_user_id=from_user_id).count()
        followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        return len(followings)
