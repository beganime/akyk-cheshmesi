from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel
from .managers import UserManager


class User(AbstractUser, UUIDTimeStampedModel):
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.CharField(max_length=160, blank=True)
    is_email_verified = models.BooleanField(default=False, db_index=True)
    registration_completed = models.BooleanField(default=False, db_index=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["is_email_verified"]),
            models.Index(fields=["registration_completed"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.username or 'pending'})"


class OneTimeCode(UUIDTimeStampedModel):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email verification"
        PASSWORD_RESET = "password_reset", "Password reset"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="one_time_codes",
        null=True,
        blank=True,
    )
    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices, db_index=True)
    code_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "user_one_time_codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["used_at"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_active(self) -> bool:
        return self.used_at is None and not self.is_expired()

    def __str__(self) -> str:
        return f"{self.email} | {self.purpose}"


class DevicePushToken(UUIDTimeStampedModel):
    class Provider(models.TextChoices):
        FCM = "fcm", "FCM"
        APNS = "apns", "APNs"

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="push_tokens",
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    provider = models.CharField(max_length=20, choices=Provider.choices, db_index=True)
    platform = models.CharField(max_length=20, choices=Platform.choices, db_index=True)
    device_id = models.CharField(max_length=128, blank=True, db_index=True)
    device_name = models.CharField(max_length=120, blank=True)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "user_device_push_tokens"
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["provider", "platform", "is_active"]),
            models.Index(fields=["device_id"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} | {self.platform} | {self.provider}"