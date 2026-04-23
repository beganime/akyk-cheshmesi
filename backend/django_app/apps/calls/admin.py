from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import CallEvent, CallParticipant, CallSession


class CallParticipantInline(TabularInline):
    model = CallParticipant
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
        "invited_at",
        "joined_at",
        "left_at",
        "duration_seconds",
    )
    fields = (
        "user",
        "role",
        "status",
        "device_platform",
        "device_name",
        "device_id",
        "is_muted",
        "is_video_enabled",
        "invited_at",
        "joined_at",
        "left_at",
        "duration_seconds",
    )
    tab = True


class CallEventInline(TabularInline):
    model = CallEvent
    extra = 0
    autocomplete_fields = ("actor",)
    readonly_fields = ("uuid", "event_type", "actor", "payload", "created_at", "updated_at")
    fields = ("event_type", "actor", "payload", "created_at")
    tab = True


@admin.register(CallSession)
class CallSessionAdmin(ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "chat",
        "initiated_by",
        "call_type",
        "status",
        "room_key",
        "answered_at",
        "ended_at",
        "duration_seconds",
        "created_at",
    )
    list_filter = (
        "call_type",
        "status",
        "created_at",
        "answered_at",
        "ended_at",
    )
    search_fields = (
        "uuid",
        "room_key",
        "chat__uuid",
        "chat__title",
        "initiated_by__email",
        "initiated_by__username",
    )
    autocomplete_fields = ("chat", "initiated_by")
    readonly_fields = (
        "uuid",
        "room_key",
        "answered_at",
        "ended_at",
        "duration_seconds",
        "created_at",
        "updated_at",
    )
    inlines = [CallParticipantInline, CallEventInline]


@admin.register(CallParticipant)
class CallParticipantAdmin(ModelAdmin):
    list_display = (
        "id",
        "session",
        "user",
        "role",
        "status",
        "device_platform",
        "is_muted",
        "is_video_enabled",
        "joined_at",
        "left_at",
        "duration_seconds",
        "created_at",
    )
    list_filter = (
        "role",
        "status",
        "device_platform",
        "is_muted",
        "is_video_enabled",
        "created_at",
    )
    search_fields = (
        "session__uuid",
        "user__email",
        "user__username",
        "device_id",
        "device_name",
    )
    autocomplete_fields = ("session", "user")
    readonly_fields = (
        "uuid",
        "invited_at",
        "joined_at",
        "left_at",
        "duration_seconds",
        "created_at",
        "updated_at",
    )


@admin.register(CallEvent)
class CallEventAdmin(ModelAdmin):
    list_display = (
        "id",
        "session",
        "event_type",
        "actor",
        "created_at",
    )
    list_filter = ("event_type", "created_at")
    search_fields = (
        "session__uuid",
        "actor__email",
        "actor__username",
        "event_type",
    )
    autocomplete_fields = ("session", "actor")
    readonly_fields = (
        "uuid",
        "session",
        "event_type",
        "actor",
        "payload",
        "created_at",
        "updated_at",
    )