from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import BotCommand, BotProfile


class BotCommandInline(TabularInline):
    model = BotCommand
    extra = 0


@admin.register(BotProfile)
class BotProfileAdmin(ModelAdmin):
    list_display = ("title", "code", "is_active")
    search_fields = ("title", "code")
    list_filter = ("is_active",)
    inlines = [BotCommandInline]


@admin.register(BotCommand)
class BotCommandAdmin(ModelAdmin):
    list_display = ("command", "bot", "is_active")
    search_fields = ("command", "response_text")
    list_filter = ("is_active", "bot")
