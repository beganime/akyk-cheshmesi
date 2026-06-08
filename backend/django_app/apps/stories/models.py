from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel


def default_story_expires_at():
    ttl_hours = getattr(settings, "STORY_TTL_HOURS", 24)
    return timezone.now() + timedelta(hours=ttl_hours)


class Story(UUIDTimeStampedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        TEXT = "text", "Text"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
    )
    media = models.ForeignKey(
        "mediafiles.UploadedMedia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
    )
    media_type = models.CharField(max_length=16, choices=MediaType.choices, db_index=True)
    caption = models.TextField(blank=True)
    background = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(default=default_story_expires_at, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "stories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["is_active", "expires_at"]),
            models.Index(fields=["media_type", "created_at"]),
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"{self.author_id} story {self.uuid}"


class StoryView(UUIDTimeStampedModel):
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="views",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="story_views",
    )
    viewed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "story_views"
        ordering = ["-viewed_at"]
        constraints = [
            models.UniqueConstraint(fields=["story", "viewer"], name="uniq_story_viewer"),
        ]
        indexes = [
            models.Index(fields=["story", "viewed_at"]),
            models.Index(fields=["viewer", "viewed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.viewer_id} viewed {self.story_id}"
