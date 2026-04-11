from rest_framework import serializers

from .models import UserContact
from .public_serializers import UserShortSerializer


class UserContactSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = UserContact
        fields = (
            "uuid",
            "source",
            "last_interaction_at",
            "is_favorite",
            "user",
        )

    def get_user(self, obj):
        return UserShortSerializer(obj.contact_user, context=self.context).data


class UserContactDetailSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = UserContact
        fields = (
            "uuid",
            "source",
            "last_interaction_at",
            "is_favorite",
            "user",
        )

    def get_user(self, obj):
        user = obj.contact_user
        return {
            "uuid": str(user.uuid),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "",
            "avatar": user.avatar.url if user.avatar else None,
            "badge": "staff" if user.is_staff else "",
        }
