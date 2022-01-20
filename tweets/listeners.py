def push_tweet_to_cache(sender, instance, created, **kwargs):
    # We store a list of tweets in Redis.
    # When one of the tweets gets updated, it might take some time to find out where it is.
    # We can invalidate the list, but for now we just don't support tweet edit.
    # A workaround is to store tweet ids in Reids, store tweet objects in Memcached.
    # However, it would require multiple cache queries, lower efficiency.
    if not created:
        return

    from tweets.services import TweetService
    TweetService.push_tweet_to_cache(instance)