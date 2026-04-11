from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AppRelease(UUIDTimeStampedModel):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"
        WEB = "web", "Web"

    version = models.CharField(max_length=40, db_index=True)
    build_number = models.CharField(max_length=32, blank=True)
    download_url = models.URLField(max_length=600)
    changelog = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    released_at = models.DateTimeField(db_index=True)
    min_android_version = models.CharField(max_length=20, blank=True)
    available_platforms = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "app_releases"
        ordering = ["-released_at", "-created_at"]
        indexes = [models.Index(fields=["version"]), models.Index(fields=["released_at"])]

    @property
    def qr_code_url(self) -> str:
        return f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={self.download_url}"

    def __str__(self) -> str:
        return f"{self.version} ({self.build_number})"
