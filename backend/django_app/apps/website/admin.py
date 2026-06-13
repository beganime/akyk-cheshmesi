from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CompanyTeamMember, SiteSettings, SupportRequest


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    list_display = ("company_name", "director_name", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("company_name", "legal_company_name", "director_name")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(CompanyTeamMember)
class CompanyTeamMemberAdmin(ModelAdmin):
    list_display = ("full_name", "role", "team", "display_order", "is_active")
    list_filter = ("team", "is_active")
    search_fields = ("full_name", "role", "email", "telegram")
    list_editable = ("display_order", "is_active")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(SupportRequest)
class SupportRequestAdmin(ModelAdmin):
    list_display = ("full_name", "topic", "preferred_contact", "status", "created_at")
    list_filter = ("status", "topic", "created_at")
    search_fields = ("full_name", "email", "phone", "message")
    readonly_fields = ("uuid", "created_at", "updated_at", "ip_address", "user_agent", "source")
