from friendships.models import Friendship


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
