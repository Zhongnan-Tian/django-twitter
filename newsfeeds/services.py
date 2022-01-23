from gatekeeper.models import GateKeeper
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


def lazy_load_newsfeeds(user_id):
    def _lazy_load(limit):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            return HBaseNewsFeed.filter(prefix=(user_id, None), limit=limit, reverse=True)
        return NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


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
        fanout_newsfeeds_main_task.delay(tweet.id, tweet.timestamp, tweet.user_id)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer
        return RedisHelper.load_objects(key, lazy_load_newsfeeds(user_id), serializer=serializer)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_object(key, newsfeed, lazy_load_newsfeeds(newsfeed.user_id))

    @classmethod
    def create(cls, **kwargs):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            newsfeed = HBaseNewsFeed.create(**kwargs)
            # manually trigger cache change as there is no listener on hbase create.
            cls.push_newsfeed_to_cache(newsfeed)
        else:
            newsfeed = NewsFeed.objects.create(**kwargs)
        return newsfeed

    @classmethod
    def batch_create(cls, batch_params):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            newsfeeds = HBaseNewsFeed.batch_create(batch_params)
        else:
            newsfeeds = [NewsFeed(**params) for params in batch_params]
            NewsFeed.objects.bulk_create(newsfeeds)

        # bulk create won't trigger post_save signal, manually push to cache.
        for newsfeed in newsfeeds:
            NewsFeedService.push_newsfeed_to_cache(newsfeed)
        return newsfeeds
