from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    badge = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "uuid",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "avatar",
            "badge",
        )

    def get_full_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or obj.username or ""

    def get_badge(self, obj):
        return "staff" if getattr(obj, "is_staff", False) else ""
