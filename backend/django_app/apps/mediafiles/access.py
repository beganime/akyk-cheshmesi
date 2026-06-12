from django.db.models import Q

from apps.mediafiles.models import UploadedMedia


def user_can_access_media(user, media: UploadedMedia) -> bool:
    if media.is_public:
        return True

    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_staff", False):
        return True

    if media.owner_id == user.id:
        return True

    if media.message_attachments.filter(
        message__chat__is_active=True,
        message__chat__members__user=user,
        message__chat__members__is_active=True,
    ).exists():
        return True

    try:
        from apps.stories.models import Story
        from apps.stories.views import visible_story_queryset

        if visible_story_queryset(user).filter(media=media).exists():
            return True
    except Exception:
        return False

    return False


def media_access_queryset_for_user(user):
    queryset = UploadedMedia.objects.filter(status=UploadedMedia.Status.UPLOADED)

    if user and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False):
        return queryset

    public_filter = Q(is_public=True)
    if not user or not getattr(user, "is_authenticated", False):
        return queryset.filter(public_filter)

    return queryset.filter(
        public_filter
        | Q(owner=user)
        | Q(message_attachments__message__chat__is_active=True)
        & Q(message_attachments__message__chat__members__user=user)
        & Q(message_attachments__message__chat__members__is_active=True)
    ).distinct()
