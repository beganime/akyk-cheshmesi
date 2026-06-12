from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import BotCommand, BotMembership, BotProfile


class BotCommandInline(TabularInline):
    model = BotCommand
    extra = 0


@admin.register(BotProfile)
class BotProfileAdmin(ModelAdmin):
    list_display = ("title", "code", "username", "owner", "is_active", "last_used_at")
    search_fields = ("title", "code", "username", "owner__email", "owner__username")
    list_filter = ("is_active", "created_at", "last_used_at")
    readonly_fields = ("uuid", "token_hash", "token_last_rotated_at", "last_used_at", "created_at", "updated_at")
    autocomplete_fields = ("owner", "user")
    inlines = [BotCommandInline]


@admin.register(BotCommand)
class BotCommandAdmin(ModelAdmin):
    list_display = ("command", "bot", "is_active")
    search_fields = ("command", "response_text")
    list_filter = ("is_active", "bot")


@admin.register(BotMembership)
class BotMembershipAdmin(ModelAdmin):
    list_display = ("bot", "chat", "is_active", "added_by", "created_at")
    search_fields = ("bot__title", "bot__username", "chat__uuid", "added_by__email")
    list_filter = ("is_active", "created_at")
    autocomplete_fields = ("bot", "chat", "added_by")
