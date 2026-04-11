from django.db import models

from apps.common.models import UUIDTimeStampedModel


class BotProfile(UUIDTimeStampedModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bot_profiles"
        ordering = ["title"]

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
