from rest_framework import serializers

from .models import AppRelease


class AppReleaseSerializer(serializers.ModelSerializer):
    qr_code_url = serializers.CharField(read_only=True)

    class Meta:
        model = AppRelease
        fields = (
            "uuid",
            "version",
            "build_number",
            "download_url",
            "changelog",
            "is_active",
            "released_at",
            "min_android_version",
            "available_platforms",
            "qr_code_url",
            "created_at",
            "updated_at",
        )
