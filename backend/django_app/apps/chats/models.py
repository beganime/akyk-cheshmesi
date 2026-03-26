from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Chat(UUIDTimeStampedModel):
    class ChatType(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"

    chat_type = models.CharField(max_length=16, choices=ChatType.choices, db_index=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="chat-avatars/", null=True, blank=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chats",
    )

    direct_key = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Sorted pair key for direct chats, e.g. uuid1:uuid2",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_public = models.BooleanField(default=False, db_index=True)
    members_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "chats"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["chat_type", "is_active"]),
            models.Index(fields=["last_message_at"]),
            models.Index(fields=["direct_key"]),
        ]

    def __str__(self) -> str:
        if self.chat_type == self.ChatType.DIRECT:
            return f"Direct chat {self.uuid}"
        return self.title or f"Group chat {self.uuid}"


class ChatMember(UUIDTimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    chat = models.ForeignKey(
        "chats.Chat",
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True, db_index=True)

    is_active = models.BooleanField(default=True, db_index=True)
    is_muted = models.BooleanField(default=False, db_index=True)
    can_send_messages = models.BooleanField(default=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    is_pinned = models.BooleanField(default=False, db_index=True)
    pinned_at = models.DateTimeField(null=True, blank=True, db_index=True)

    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "chat_members"
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(fields=["chat", "user"], name="uniq_chat_member"),
        ]
        indexes = [
            models.Index(fields=["chat", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role"]),
            models.Index(fields=["last_read_at"]),
            models.Index(fields=["is_pinned", "pinned_at"]),
            models.Index(fields=["is_archived", "archived_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.chat_id} ({self.role})"