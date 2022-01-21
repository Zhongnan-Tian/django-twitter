from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from tweets.models import Tweet
from likes.models import Like
from utils.memcached_helper import MemcachedHelper
from comments.listeners import incr_comments_count, decr_comments_count
from django.db.models.signals import post_save, pre_delete


class Comment(models.Model):
    """
    In this version, comment is just added for tweet, not for other comment.
    """
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    tweet = models.ForeignKey(Tweet, null=True, on_delete=models.SET_NULL)
    content = models.TextField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # we have the use case that sorting all comments of a specific tweet.
        index_together = (('tweet', 'created_at'),)

    def __str__(self):
        return '{} - {} says {} at tweet {}'.format(
            self.created_at,
            self.user,
            self.content,
            self.tweet_id,
        )

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Comment),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)

post_save.connect(incr_comments_count, sender=Comment)
pre_delete.connect(decr_comments_count, sender=Comment)