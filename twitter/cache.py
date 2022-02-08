# memcached standard keys: '{}:{}'.format(model_class.__name__, object_id)
# Followings are non-standard keys
FOLLOWINGS_PATTERN = 'followings:{user_id}'
USER_PROFILE_PATTERN = 'userprofile:{user_id}'

# redis
USER_TWEETS_PATTERN = 'user_tweets:{user_id}'
USER_NEWSFEEDS_PATTERN = 'user_newsfeeds:{user_id}'
