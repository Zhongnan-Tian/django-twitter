from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from utils.time_helpers import utc_now
from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES


class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at')

    def __str__(self):
        # the content to display when call print(tweet instance).
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def hours_to_now(self):
        # datetime.now doesn't contain timezone，Use utc_now() to contain timezone.
        return (utc_now() - self.created_at).seconds // 3600

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')


class TweetPhoto(models.Model):
    # which tweet this photo is for
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # who uploaded this photo，
    # Although the person can be fetched from tweet, it provides benefits if
    # photo model stores this info as well.
    # For example, a person who uploaded illegal photos many times, we can pay more attention to him/her.
    # We can also ban all photos of specific user.
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    file = models.FileField()
    order = models.IntegerField(default=0)

    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # has_deleted is used as a mark for soft delete，
    # When a photo is deleted by user，set has_deleted: true，
    # After some time, the photo can be hard deleted asynchronously.
    # This is because hard delete may take some time.
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
            ('tweet', 'order'),
        )

    def __str__(self):
        return f'{self.tweet_id}: {self.file}'
