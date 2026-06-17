from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(ModelAdmin):
    list_display = (
        "version",
        "build_number",
        "platform",
        "channel",
        "store_status",
        "released_at",
        "is_active",
        "is_public",
    )
    list_filter = ("platform", "channel", "store_status", "is_active", "is_public", "released_at")
    search_fields = ("version", "build_number", "download_url", "google_play_url", "testflight_url")
    readonly_fields = ("uuid", "created_at", "updated_at", "file_size_bytes")
    fieldsets = (
        ("Версия", {"fields": ("version", "build_number", "platform", "channel", "store_status")}),
        ("Файл и ссылки", {"fields": ("package_file", "download_url", "google_play_url", "testflight_url", "file_size_bytes")}),
        ("Публикация", {"fields": ("released_at", "is_active", "is_public", "min_android_version", "available_platforms")}),
        ("Описание", {"fields": ("changelog",)}),
        ("Системные поля", {"fields": ("uuid", "created_at", "updated_at")}),
    )
