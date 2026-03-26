from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(ModelAdmin):
    list_display = (
        "id",
        "reporter",
        "complaint_type",
        "reason",
        "status",
        "reported_user",
        "chat",
        "message",
        "created_at",
    )
    list_filter = ("complaint_type", "reason", "status", "created_at")
    search_fields = (
        "reporter__email",
        "reporter__username",
        "reported_user__email",
        "reported_user__username",
        "description",
        "resolution_note",
    )
    autocomplete_fields = ("reporter", "reported_user", "chat", "message", "reviewed_by")