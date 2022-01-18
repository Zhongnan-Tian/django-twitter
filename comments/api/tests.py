from testing.testcases import TestCase
from rest_framework.test import APIClient
from django.utils import timezone
from comments.models import Comment

COMMENT_URL = '/api/comments/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'

class CommentApiTests(TestCase):

    def setUp(self):
        self.user1 = self.create_user('user1')
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(self.user1)
        self.user2 = self.create_user('user2')
        self.user2_client = APIClient()
        self.user2_client.force_authenticate(self.user2)

        self.tweet = self.create_tweet(self.user1)

    def test_create(self):
        # anonymous user x
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # no parameters x
        response = self.user1_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # tweet_id only x
        response = self.user1_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # content only x
        response = self.user1_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content too long
        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')

    def test_destroy(self):
        comment = self.create_comment(self.user1, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # anonymous x
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # not the author x
        response = self.user2_client.delete(url)
        self.assertEqual(response.status_code, 403)

        count = Comment.objects.count()
        response = self.user1_client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.user1, self.tweet, 'original')
        another_tweet = self.create_tweet(self.user2)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # anonymous user x
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)

        # not the author x
        response = self.user2_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, 'new')

        # update anything other than content x
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.user1_client.put(url, {
            'content': 'new',
            'user_id': self.user2.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.user1)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        # without tweet_id x
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # with tweet_id, no comments yet
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # create comments
        self.create_comment(self.user1, self.tweet, '1')
        self.create_comment(self.user2, self.tweet, '2')
        self.create_comment(self.user2, self.create_tweet(self.user2), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        # comments should sort by time
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # request parameters user_id and tweet_id, only tweet_id is effective in filter
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.user1.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.user1)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.user2_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.user1, tweet)
        response = self.user2_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.user2, tweet)
        self.create_newsfeed(self.user2, tweet)
        response = self.user2_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['results'][0]['tweet']['comments_count'], 2)
