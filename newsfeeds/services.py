from newsfeeds.models import NewsFeed
from friendships.services import FriendshipService


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # wrong approach
        # we cannot put db operations inside for loop，This is slow and inefficient.
        # for follower in FriendshipService.get_followers(tweet.user):
        #     NewsFeed.objects.create(
        #         user=follower,
        #         tweet=tweet,
        #     )
        # correct approach: use bulk_create so that there is only one insert.
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet)
            for follower in FriendshipService.get_followers(tweet.user)
        ]
        # the user who created the tweet should be able to see the tweet as well.
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
        NewsFeed.objects.bulk_create(newsfeeds)
