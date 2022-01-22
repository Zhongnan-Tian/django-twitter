from newsfeeds.models import NewsFeed
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper
from newsfeeds.tasks import fanout_newsfeeds_main_task


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # create a fanout task in message queue.
        # Any worker who subscribes to the message queue can take the task.
        # worker will execute fanout_newsfeeds_task code in an async way.
        # .delay will start and finish immediately so the worker operation
        # won't block/delay users。
        # Note parameter inside .delay has to be something which can be
        # serialized by celery，Pass tweet.id instead of tweet，because celery
        # doesn't know how to serialize Tweet.
        fanout_newsfeeds_main_task.delay(tweet.id, tweet.user_id)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by(
            '-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(key, queryset)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by(
            '-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_object(key, newsfeed, queryset)
