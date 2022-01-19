from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase


class FriendshipServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.test1 = self.create_user('test1')
        self.test2 = self.create_user('test2')

    def test_get_followings(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')
        for to_user in [user1, user2, self.test2]:
            Friendship.objects.create(from_user=self.test1, to_user=to_user)

        user_id_set = FriendshipService.get_following_user_id_set(self.test1.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id, self.test2.id})

        Friendship.objects.filter(from_user=self.test1, to_user=self.test2).delete()
        user_id_set = FriendshipService.get_following_user_id_set(self.test1.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id})