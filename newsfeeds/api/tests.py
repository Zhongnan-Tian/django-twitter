from django.conf import settings
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        super(NewsFeedApiTests, self).setUp()
        self.testuser1 = self.create_user('testuser1')
        self.testuser1_client = APIClient()
        self.testuser1_client.force_authenticate(self.testuser1)

        self.testuser2 = self.create_user('testuser2')
        self.testuser2_client = APIClient()
        self.testuser2_client.force_authenticate(self.testuser2)

        # create followings and followers for testuser2
        for i in range(2):
            follower = self.create_user('testuser2_follower{}'.format(i))
            Friendship.objects.create(from_user=follower,
                                      to_user=self.testuser2)
        for i in range(3):
            following = self.create_user('testuser2_following{}'.format(i))
            Friendship.objects.create(from_user=self.testuser2,
                                      to_user=following)

    def test_list(self):
        # cannot view newsfeeds without login
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 403)

        # cannot use post method
        response = self.testuser1_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 405)

        # no tweets in newsfeeds
        response = self.testuser1_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        # post a tweet and should see the tweet in newsfeeds
        self.testuser1_client.post(POST_TWEETS_URL, {'content': 'Hello World'})
        response = self.testuser1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)

        # follow another user
        self.testuser1_client.post(FOLLOW_URL.format(self.testuser2.id))
        # the user posts tweet
        response = self.testuser2_client.post(POST_TWEETS_URL, {
            'content': 'Hello Twitter',
        })
        posted_tweet_id = response.data['id']
        # the tweet should be displayed in current user's newsfeeds
        response = self.testuser1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'],
                         posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user=self.testuser1, tweet=tweet)
            newsfeeds.append(newsfeed)

        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.testuser1_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.testuser1_client.get(
            NEWSFEEDS_URL,
            {'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.testuser1_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.testuser1, tweet=tweet)

        response = self.testuser1_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        profile = self.testuser2.profile
        profile.nickname = 'huanglaoxie'
        profile.save()

        self.assertEqual(self.testuser1.username, 'testuser1')
        self.create_newsfeed(self.testuser2, self.create_tweet(self.testuser1))
        self.create_newsfeed(self.testuser2, self.create_tweet(self.testuser2))

        response = self.testuser2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'testuser2')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huanglaoxie')
        self.assertEqual(results[1]['tweet']['user']['username'], 'testuser1')

        self.testuser1.username = 'testuser1chong'
        self.testuser1.save()
        profile.nickname = 'huangyaoshi'
        profile.save()

        response = self.testuser2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'testuser2')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huangyaoshi')
        self.assertEqual(results[1]['tweet']['user']['username'],
                         'testuser1chong')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.testuser1, 'content1')
        self.create_newsfeed(self.testuser2, tweet)
        response = self.testuser2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'testuser1')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.testuser1.username = 'testuser1chong'
        self.testuser1.save()
        response = self.testuser2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'],
                         'testuser1chong')

        # update content
        tweet.content = 'content2'
        tweet.save()
        response = self.testuser2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')

    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL,
                                  {'created_at__lt': created_at__lt})
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = 20
        users = [self.create_user('user{}'.format(i)) for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5],
                                      content='feed{}'.format(i))
            feed = self.create_newsfeed(self.testuser1, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # only cached list_limit objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(
            self.testuser1.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.testuser1)
        self.assertEqual(queryset.count(), list_limit + page_size)

        results = self._paginate_to_get_newsfeeds(self.testuser1_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(newsfeeds[i].id, results[i]['id'])

        # a followed user create a new tweet
        self.create_friendship(self.testuser1, self.testuser2)
        new_tweet = self.create_tweet(self.testuser2, 'a new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.testuser1_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()

        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()