from notifications.models import Notification
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'


class NotificationTests(TestCase):

    def setUp(self):
        self.user1, self.user1_client = self.create_user_and_client('user1')
        self.user2, self.user2_client = self.create_user_and_client('user2')
        self.user2_tweet = self.create_tweet(self.user2)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.user2_tweet.id,
            'content': 'lol',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.user1_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.user2_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)


class NotificationApiTests(TestCase):

    def setUp(self):
        self.user1, self.user1_client = self.create_user_and_client('user1')
        self.user2, self.user2_client = self.create_user_and_client('user2')
        self.user1_tweet = self.create_tweet(self.user1)

    def test_unread_count(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.user1_tweet.id,
        })

        url = '/api/notifications/unread-count/'
        response = self.user1_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.user1, self.user1_tweet)
        self.user2_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        response = self.user1_client.get(url)
        self.assertEqual(response.data['unread_count'], 2)

    def test_mark_all_as_read(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.user1_tweet.id,
        })
        comment = self.create_comment(self.user1, self.user1_tweet)
        self.user2_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        unread_url = '/api/notifications/unread-count/'
        response = self.user1_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        mark_url = '/api/notifications/mark-all-as-read/'
        response = self.user1_client.get(mark_url)
        self.assertEqual(response.status_code, 405)
        response = self.user1_client.post(mark_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.user1_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.user1_tweet.id,
        })
        comment = self.create_comment(self.user1, self.user1_tweet)
        self.user2_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # anonymous user cannot visit the api
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 403)
        # user2 cannot see any notifications
        response = self.user2_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        # user1 can see two notifications
        response = self.user1_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        notification = self.user1.notifications.first()
        notification.unread = False
        notification.save()
        response = self.user1_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.user1_client.get(NOTIFICATION_URL, {'unread': True})
        self.assertEqual(response.data['count'], 1)
        response = self.user1_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)

    def test_update(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.user1_tweet.id,
        })
        comment = self.create_comment(self.user1, self.user1_tweet)
        self.user2_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        notification = self.user1.notifications.first()

        url = '/api/notifications/{}/'.format(notification.id)
        # post x, put V
        response = self.user2_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, 405)
        # notification unread status cannot be updated by others
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 403)
        # queryset is for current logged in user，so code status is 404 instead of 403
        response = self.user2_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 404)
        # set unread successfully
        response = self.user1_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 200)
        unread_url = '/api/notifications/unread-count/'
        response = self.user1_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 1)

        # set unread successfully
        response = self.user1_client.put(url, {'unread': True})
        response = self.user1_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)
        # must contain unread
        response = self.user1_client.put(url, {'verb': 'newverb'})
        self.assertEqual(response.status_code, 400)
        # cannot update other attributes other than unread
        response = self.user1_client.put(url,
                                         {'verb': 'newverb', 'unread': False})
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertNotEqual(notification.verb, 'newverb')
