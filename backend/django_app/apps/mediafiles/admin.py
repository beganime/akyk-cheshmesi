from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import MessageAttachment, UploadedMedia


@admin.register(UploadedMedia)
class UploadedMediaAdmin(ModelAdmin):
    list_display = (
        "id",
        "owner",
        "original_name",
        "content_type",
        "size",
        "media_kind",
        "storage_provider",
        "status",
        "created_at",
    )
    list_filter = ("media_kind", "storage_provider", "status", "created_at")
    search_fields = ("original_name", "object_key", "owner__email", "owner__username")
    autocomplete_fields = ("owner",)


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(ModelAdmin):
    list_display = ("id", "message", "media", "sort_order", "created_at")
    search_fields = ("message__uuid", "media__original_name")
    autocomplete_fields = ("message", "media")