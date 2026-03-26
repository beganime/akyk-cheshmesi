from django.conf import settings
from django.db import models

from apps.chats.models import Chat
from apps.common.models import UUIDTimeStampedModel
from apps.messaging.models import Message


class Complaint(UUIDTimeStampedModel):
    class ComplaintType(models.TextChoices):
        USER = "user", "User"
        CHAT = "chat", "Chat"
        MESSAGE = "message", "Message"
        APP = "app", "App"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        ABUSE = "abuse", "Abuse"
        FRAUD = "fraud", "Fraud"
        HARASSMENT = "harassment", "Harassment"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_REVIEW = "in_review", "In review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_complaints",
    )
    complaint_type = models.CharField(max_length=20, choices=ComplaintType.choices, db_index=True)
    reason = models.CharField(max_length=20, choices=Reason.choices, db_index=True)
    description = models.TextField(blank=True)

    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_complaints",
    )
    chat = models.ForeignKey(
        Chat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_complaints",
    )
    resolution_note = models.TextField(blank=True)

    class Meta:
        db_table = "complaints"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reporter", "status"]),
            models.Index(fields=["complaint_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.reporter_id} / {self.complaint_type} / {self.reason}"