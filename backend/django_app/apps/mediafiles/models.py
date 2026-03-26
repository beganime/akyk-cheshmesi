from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class UploadedMedia(UUIDTimeStampedModel):
    class StorageProvider(models.TextChoices):
        LOCAL = "local", "Local"
        S3 = "s3", "S3"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UPLOADED = "uploaded", "Uploaded"
        FAILED = "failed", "Failed"

    class MediaKind(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        FILE = "file", "File"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_media",
    )
    file = models.FileField(upload_to="uploads/%Y/%m/%d/", null=True, blank=True)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    media_kind = models.CharField(
        max_length=20,
        choices=MediaKind.choices,
        default=MediaKind.FILE,
        db_index=True,
    )
    storage_provider = models.CharField(
        max_length=20,
        choices=StorageProvider.choices,
        default=StorageProvider.LOCAL,
        db_index=True,
    )
    object_key = models.CharField(max_length=500, blank=True, db_index=True)
    bucket_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    checksum = models.CharField(max_length=128, blank=True)
    is_public = models.BooleanField(default=False)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "uploaded_media"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "media_kind"]),
            models.Index(fields=["object_key"]),
        ]

    def __str__(self) -> str:
        return self.original_name


class MessageAttachment(UUIDTimeStampedModel):
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    media = models.ForeignKey(
        "mediafiles.UploadedMedia",
        on_delete=models.CASCADE,
        related_name="message_attachments",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "message_attachments"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["message", "media"], name="uniq_message_media_attachment"),
        ]

    def __str__(self) -> str:
        return f"{self.message_id} -> {self.media_id}"