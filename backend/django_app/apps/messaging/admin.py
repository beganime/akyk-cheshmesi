from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Message, MessageReceipt


class MessageReceiptInline(TabularInline):
    model = MessageReceipt
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("uuid", "created_at", "updated_at")
    tab = True


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "chat",
        "sender",
        "message_type",
        "short_text",
        "is_edited",
        "is_deleted",
        "created_at",
    )
    list_filter = ("message_type", "is_edited", "is_deleted", "created_at")
    search_fields = ("uuid", "text", "chat__uuid", "sender__email", "sender__username")
    autocomplete_fields = ("chat", "sender", "reply_to")
    readonly_fields = ("uuid", "created_at", "updated_at", "edited_at", "deleted_at")
    inlines = [MessageReceiptInline]

    @admin.display(description="Text")
    def short_text(self, obj):
        if not obj.text:
            return "-"
        return obj.text[:80]


@admin.register(MessageReceipt)
class MessageReceiptAdmin(ModelAdmin):
    list_display = (
        "id",
        "message",
        "user",
        "delivered_at",
        "read_at",
        "created_at",
    )
    list_filter = ("delivered_at", "read_at", "created_at")
    search_fields = ("message__uuid", "user__email", "user__username")
    autocomplete_fields = ("message", "user")
    readonly_fields = ("uuid", "created_at", "updated_at")