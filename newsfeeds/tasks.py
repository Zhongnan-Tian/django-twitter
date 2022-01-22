from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.time_constants import ONE_HOUR
from newsfeeds.constants import FANOUT_BATCH_SIZE


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, follower_ids):
    # import inside to avoid dependency circular
    from newsfeeds.services import NewsFeedService

    # wrong approach
    # we cannot put db operations inside for loop，This is slow and inefficient.
    # for follower_id in follower_ids:
    #     NewsFeed.objects.create(user_id=follower_id, tweet_id=tweet_id)
    # correct approach: use bulk_create so that there is only one insert.
    newsfeeds = [
        NewsFeed(user_id=follower_id, tweet_id=tweet_id)
        for follower_id in follower_ids
    ]
    NewsFeed.objects.bulk_create(newsfeeds)

    # bulk create won't trigger post_save signal，manually push to cache
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeed_to_cache(newsfeed)

    return "{} newsfeeds created".format(len(newsfeeds))


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, tweet_user_id):
    # Create for the author first.
    # Make sure the tweet author can see his/her tweet in his/her newsfeeds asap.
    NewsFeed.objects.create(user_id=tweet_user_id, tweet_id=tweet_id)

    # Get all follower ids，divide by batch size
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0

    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )