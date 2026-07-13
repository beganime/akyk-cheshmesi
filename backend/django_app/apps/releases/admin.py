from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
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
        "package_size",
        "download_package",
        "released_at",
        "is_active",
        "is_public",
    )
    list_filter = ("platform", "channel", "store_status", "is_active", "is_public", "released_at")
    search_fields = ("version", "build_number", "download_url", "google_play_url", "testflight_url")
    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
        "file_size_bytes",
        "package_size",
        "download_package",
    )
    actions = ("publish_releases", "move_to_draft")
    list_per_page = 30
    save_on_top = True
    fieldsets = (
        ("Версия", {"fields": ("version", "build_number", "platform", "channel", "store_status")}),
        (
            "APK и ссылки",
            {
                "fields": (
                    "package_file",
                    "package_size",
                    "download_package",
                    "download_url",
                    "google_play_url",
                    "testflight_url",
                ),
                "description": "APK до 256 МБ загружается потоково. После сохранения проверьте ссылку скачивания.",
            },
        ),
        ("Публикация", {"fields": ("released_at", "is_active", "is_public", "min_android_version", "available_platforms")}),
        ("Что изменилось", {"fields": ("changelog",)}),
        ("Системные поля", {"classes": ("collapse",), "fields": ("uuid", "file_size_bytes", "created_at", "updated_at")}),
    )

    @admin.display(description="Размер", ordering="file_size_bytes")
    def package_size(self, obj):
        size = int(obj.file_size_bytes or 0)
        if not size:
            return "—"
        return f"{size / (1024 * 1024):.1f} МБ"

    @admin.display(description="Скачать")
    def download_package(self, obj):
        if not obj:
            return "—"
        if obj.package_file:
            url = reverse("app-release-download", kwargs={"release_uuid": obj.uuid})
        else:
            url = obj.download_url or obj.google_play_url or obj.testflight_url
        if not url:
            return "—"
        return format_html(
            '<a class="button" href="{}" target="_blank" rel="noopener">Скачать сборку</a>',
            url,
        )

    @admin.action(description="Опубликовать выбранные релизы")
    def publish_releases(self, request, queryset):
        updated = queryset.update(
            store_status=AppRelease.StoreStatus.LIVE,
            is_active=True,
            is_public=True,
        )
        self.message_user(request, f"Опубликовано релизов: {updated}.", messages.SUCCESS)

    @admin.action(description="Вернуть выбранные релизы в черновики")
    def move_to_draft(self, request, queryset):
        updated = queryset.update(store_status=AppRelease.StoreStatus.DRAFT, is_public=False)
        self.message_user(request, f"Переведено в черновики: {updated}.", messages.SUCCESS)
