from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import OneTimeCode, User, UserContact


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ("-date_joined",)
    list_display = (
        "id",
        "uuid",
        "email",
        "username",
        "is_email_verified",
        "registration_completed",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "is_email_verified",
        "registration_completed",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = ("email", "username", "uuid")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "uuid",
                    "username",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "phone_number",
                    "avatar",
                    "bio",
                    "show_online_status",
                    "is_email_verified",
                    "registration_completed",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = ("uuid", "date_joined", "last_login")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )


@admin.register(OneTimeCode)
class OneTimeCodeAdmin(ModelAdmin):
    list_display = (
        "id",
        "email",
        "purpose",
        "expires_at",
        "used_at",
        "created_at",
    )
    list_filter = ("purpose", "used_at", "created_at")
    search_fields = ("email",)
    readonly_fields = (
        "uuid",
        "user",
        "email",
        "purpose",
        "code_hash",
        "attempts",
        "expires_at",
        "used_at",
        "meta",
        "created_at",
        "updated_at",
    )


@admin.register(UserContact)
class UserContactAdmin(ModelAdmin):
    list_display = ("id", "owner", "contact_user", "source", "last_interaction_at", "is_favorite")
    list_filter = ("source", "is_favorite", "last_interaction_at")
    search_fields = ("owner__email", "contact_user__email", "owner__username", "contact_user__username")
