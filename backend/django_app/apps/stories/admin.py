from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Story, StoryView


@admin.register(Story)
class StoryAdmin(ModelAdmin):
    list_display = ("id", "uuid", "author", "media_type", "is_active", "expires_at", "created_at")
    list_filter = ("media_type", "is_active", "created_at", "expires_at")
    search_fields = ("uuid", "author__email", "author__username", "caption")
    autocomplete_fields = ("author", "media")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(StoryView)
class StoryViewAdmin(ModelAdmin):
    list_display = ("id", "story", "viewer", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("story__uuid", "viewer__email", "viewer__username")
    autocomplete_fields = ("story", "viewer")
    readonly_fields = ("uuid", "viewed_at", "created_at", "updated_at")
