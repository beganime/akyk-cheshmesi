from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AppRelease(UUIDTimeStampedModel):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"
        WEB = "web", "Web"

    class ReleaseChannel(models.TextChoices):
        INTERNAL = "internal", "Internal"
        TESTING = "testing", "Testing"
        BETA = "beta", "Beta"
        PRODUCTION = "production", "Production"

    class StoreStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        TESTING = "testing", "Testing"
        REVIEW = "review", "On review"
        LIVE = "live", "Live"

    version = models.CharField(max_length=40, db_index=True)
    build_number = models.CharField(max_length=32, blank=True)
    platform = models.CharField(max_length=24, choices=Platform.choices, default=Platform.ANDROID, db_index=True)
    channel = models.CharField(max_length=24, choices=ReleaseChannel.choices, default=ReleaseChannel.TESTING, db_index=True)
    store_status = models.CharField(max_length=24, choices=StoreStatus.choices, default=StoreStatus.DRAFT, db_index=True)
    package_file = models.FileField(upload_to="app_packages/android/", blank=True, null=True)
    download_url = models.URLField(max_length=600, blank=True)
    google_play_url = models.URLField(max_length=600, blank=True)
    testflight_url = models.URLField(max_length=600, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0, blank=True)
    changelog = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    released_at = models.DateTimeField(db_index=True)
    min_android_version = models.CharField(max_length=20, blank=True)
    available_platforms = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "app_releases"
        ordering = ["-released_at", "-created_at"]
        indexes = [
            models.Index(fields=["version"]),
            models.Index(fields=["released_at"]),
            models.Index(fields=["platform", "is_active"]),
            models.Index(fields=["channel", "store_status"]),
        ]

    @property
    def package_url(self) -> str:
        if self.package_file:
            return self.package_file.url
        return ""

    @property
    def resolved_download_url(self) -> str:
        return self.package_url or self.download_url or self.google_play_url or self.testflight_url

    def save(self, *args, **kwargs):
        if self.package_file and not self.file_size_bytes:
            try:
                self.file_size_bytes = self.package_file.size
            except Exception:
                self.file_size_bytes = 0
        if self.platform and self.platform not in self.available_platforms:
            self.available_platforms = [*self.available_platforms, self.platform]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.platform} {self.version} ({self.build_number})"
