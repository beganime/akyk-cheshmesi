import uuid

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class CallSession(UUIDTimeStampedModel):
    class CallType(models.TextChoices):
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        RINGING = "ringing", "Ringing"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELED = "canceled", "Canceled"
        MISSED = "missed", "Missed"
        ENDED = "ended", "Ended"
        FAILED = "failed", "Failed"
        BUSY = "busy", "Busy"

    chat = models.ForeignKey(
        "chats.Chat",
        on_delete=models.CASCADE,
        related_name="calls",
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="initiated_call_sessions",
    )
    call_type = models.CharField(
        max_length=16,
        choices=CallType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    room_key = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        default="",
        blank=True,
    )
    answered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "call_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["chat", "created_at"]),
            models.Index(fields=["initiated_by", "created_at"]),
            models.Index(fields=["call_type", "status"]),
            models.Index(fields=["answered_at"]),
            models.Index(fields=["ended_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.room_key:
            self.room_key = f"call-{uuid.uuid4().hex}"
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.call_type} call {self.uuid} [{self.status}]"


class CallParticipant(UUIDTimeStampedModel):
    class Role(models.TextChoices):
        CALLER = "caller", "Caller"
        CALLEE = "callee", "Callee"
        PARTICIPANT = "participant", "Participant"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        RINGING = "ringing", "Ringing"
        JOINED = "joined", "Joined"
        DECLINED = "declined", "Declined"
        MISSED = "missed", "Missed"
        LEFT = "left", "Left"
        FAILED = "failed", "Failed"
        BUSY = "busy", "Busy"

    session = models.ForeignKey(
        "calls.CallSession",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="call_participants",
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.PARTICIPANT,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.INVITED,
        db_index=True,
    )
    invited_at = models.DateTimeField(auto_now_add=True, db_index=True)
    joined_at = models.DateTimeField(null=True, blank=True, db_index=True)
    left_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    device_id = models.CharField(max_length=128, blank=True, db_index=True)
    device_platform = models.CharField(max_length=32, blank=True, db_index=True)
    device_name = models.CharField(max_length=128, blank=True)

    is_muted = models.BooleanField(default=False, db_index=True)
    is_video_enabled = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "call_participants"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="uniq_call_participant_session_user",
            ),
        ]
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["role"]),
            models.Index(fields=["joined_at"]),
            models.Index(fields=["left_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.session_id} [{self.status}]"


class CallEvent(UUIDTimeStampedModel):
    session = models.ForeignKey(
        "calls.CallSession",
        on_delete=models.CASCADE,
        related_name="events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_events",
    )
    event_type = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "call_events"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} for {self.session_id}"