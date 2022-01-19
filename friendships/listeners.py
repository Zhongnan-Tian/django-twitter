def friendship_changed(sender, instance, **kwargs):
    # import inside to avoid dependency circular
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(instance.from_user_id)
