import uuid

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Message(UUIDTimeStampedModel):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        SYSTEM = "system", "System"
        STICKER = "sticker", "Sticker"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        FILE = "file", "File"
        AUDIO = "audio", "Audio"

    chat = models.ForeignKey(
        "chats.Chat",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    client_uuid = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Idempotency key from mobile client / Go service",
    )
    message_type = models.CharField(
        max_length=16,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        db_index=True,
    )
    text = models.TextField(blank=True)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_edited = models.BooleanField(default=False, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["chat", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
            models.Index(fields=["message_type"]),
            models.Index(fields=["reply_to"]),
            models.Index(fields=["is_deleted", "-created_at"]),
            models.Index(fields=["client_uuid"]),
        ]

    def __str__(self) -> str:
        return f"Message {self.uuid} in chat {self.chat_id}"


class MessageReceipt(UUIDTimeStampedModel):
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_receipts",
    )
    delivered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "message_receipts"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="uniq_message_receipt"),
        ]
        indexes = [
            models.Index(fields=["message", "user"]),
            models.Index(fields=["user", "read_at"]),
            models.Index(fields=["user", "delivered_at"]),
        ]

    def __str__(self) -> str:
        return f"Receipt for {self.message_id} -> {self.user_id}"


class MessageUserState(UUIDTimeStampedModel):
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        related_name="user_states",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_states",
    )
    is_hidden = models.BooleanField(default=False, db_index=True)
    hidden_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "message_user_states"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="uniq_message_user_state"),
        ]
        indexes = [
            models.Index(fields=["user", "is_hidden"]),
            models.Index(fields=["message", "user"]),
            models.Index(fields=["hidden_at"]),
        ]

    def __str__(self) -> str:
        return f"Message state {self.message_id} -> {self.user_id}"