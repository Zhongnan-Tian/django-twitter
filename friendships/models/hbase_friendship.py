from django_hbase import models


class HBaseFollowing(models.HBaseModel):
    """
    Store the users that from_user_id follows，
    row_key orders by from_user_id + created_at
    Support queries：
     - A's followings, order by time
     - A's followings, in a time period
     - A's followings (top X) before/after a timestamp
    """
    # row key
    from_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    # column key
    to_user_id = models.IntegerField(column_family='cf')

    class Meta:
        table_name = 'twitter_followings'
        row_key = ('from_user_id', 'created_at')


class HBaseFollower(models.HBaseModel):
    """
    Store the users who follow to_user_id，
    row_key orders by to_user_id + created_at
    Support queries：
     - A's followers, order by time
     - A's followers, in a time period
     - A's followers (top X) before/after a timestamp
    """
    # row key
    to_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    # column key
    from_user_id = models.IntegerField(column_family='cf')

    class Meta:
        table_name = 'twitter_followers'
        row_key = ('to_user_id', 'created_at')