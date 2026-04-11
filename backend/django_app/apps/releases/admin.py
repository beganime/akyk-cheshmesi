from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(ModelAdmin):
    list_display = (
        "version",
        "build_number",
        "released_at",
        "is_active",
    )
    list_filter = ("is_active", "released_at")
    search_fields = ("version", "build_number", "download_url")
    readonly_fields = ("uuid", "created_at", "updated_at")
