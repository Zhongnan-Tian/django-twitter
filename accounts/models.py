from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    # One2One field will create unique index to ensure that
    # no multiple UserProfile pointing to one User.
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    # Django has ImageField，Try to avoid using it as it is problematic，
    # Use FileField here. Save as file，Visit by file url.
    avatar = models.FileField(null=True)
    # After a user is created, there is an object called user profile.
    # At this time, user nickname is not set yet, so set null=True.
    nickname = models.CharField(null=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} {}'.format(self.user, self.nickname)


# Define a property method for profile. Implant it into user model.
# user_instance.profile will call get_or_create to get the profile object.
def get_profile(user):
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    # cache profile to user instance properies，
    # Avoid hitting to db multiple times when querying the same user instance's profile info.
    setattr(user, '_cached_user_profile', profile)
    return profile


# Add property profile to User Model
User.profile = property(get_profile)
