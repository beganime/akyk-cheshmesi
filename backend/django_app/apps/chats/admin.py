from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Chat, ChatMember


class ChatMemberInline(TabularInline):
    model = ChatMember
    extra = 0
    autocomplete_fields = ("user",)
    fields = (
        "user",
        "role",
        "is_active",
        "is_muted",
        "is_pinned",
        "is_archived",
        "can_send_messages",
        "last_read_at",
        "joined_at",
    )
    readonly_fields = ("joined_at",)
    tab = True


@admin.register(Chat)
class ChatAdmin(ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "chat_type",
        "title",
        "creator",
        "members_count",
        "is_active",
        "is_public",
        "last_message_at",
        "created_at",
    )
    list_filter = ("chat_type", "is_active", "is_public", "created_at")
    search_fields = ("uuid", "title", "description", "direct_key")
    readonly_fields = ("uuid", "members_count", "last_message_at", "created_at", "updated_at")
    autocomplete_fields = ("creator",)
    inlines = [ChatMemberInline]


@admin.register(ChatMember)
class ChatMemberAdmin(ModelAdmin):
    list_display = (
        "id",
        "chat",
        "user",
        "role",
        "is_active",
        "is_muted",
        "is_pinned",
        "is_archived",
        "can_send_messages",
        "last_read_at",
        "joined_at",
    )
    list_filter = (
        "role",
        "is_active",
        "is_muted",
        "is_pinned",
        "is_archived",
        "can_send_messages",
        "joined_at",
    )
    search_fields = ("chat__uuid", "chat__title", "user__email", "user__username")
    autocomplete_fields = ("chat", "user")
    readonly_fields = ("uuid", "joined_at", "created_at", "updated_at")