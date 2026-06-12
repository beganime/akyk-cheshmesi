from django.db import models
from django.conf import settings

from apps.common.models import UUIDTimeStampedModel


def default_bot_scopes():
    return ["send_message"]


class BotProfile(UUIDTimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_bots",
        null=True,
        blank=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="bot_profile",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=50, unique=True, db_index=True)
    username = models.CharField(max_length=32, unique=True, db_index=True, null=True, blank=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="bot-avatars/", null=True, blank=True)
    token_hash = models.CharField(max_length=256, blank=True)
    token_last_rotated_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=default_bot_scopes, blank=True)
    webhook_url = models.URLField(blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bot_profiles"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["username"]),
            models.Index(fields=["last_used_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class BotCommand(UUIDTimeStampedModel):
    bot = models.ForeignKey(BotProfile, on_delete=models.CASCADE, related_name="commands")
    command = models.CharField(max_length=80, db_index=True)
    response_text = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bot_commands"
        ordering = ["command"]
        constraints = [models.UniqueConstraint(fields=["bot", "command"], name="uniq_bot_command")]

    def __str__(self) -> str:
        return f"{self.bot.code}: {self.command}"


class BotMembership(UUIDTimeStampedModel):
    bot = models.ForeignKey(BotProfile, on_delete=models.CASCADE, related_name="memberships")
    chat = models.ForeignKey("chats.Chat", on_delete=models.CASCADE, related_name="bot_memberships")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_bot_memberships",
    )
    scopes = models.JSONField(default=default_bot_scopes, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bot_memberships"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["bot", "chat"], name="uniq_bot_chat_membership"),
        ]
        indexes = [
            models.Index(fields=["chat", "is_active"]),
            models.Index(fields=["bot", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.bot_id} in chat {self.chat_id}"
