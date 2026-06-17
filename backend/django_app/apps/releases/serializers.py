from urllib.parse import quote_plus

from rest_framework import serializers

from .models import AppRelease


class AppReleaseSerializer(serializers.ModelSerializer):
    package_url = serializers.SerializerMethodField()
    resolved_download_url = serializers.CharField(read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = AppRelease
        fields = (
            "uuid",
            "version",
            "build_number",
            "platform",
            "channel",
            "store_status",
            "package_url",
            "download_url",
            "resolved_download_url",
            "google_play_url",
            "testflight_url",
            "file_size_bytes",
            "changelog",
            "is_active",
            "is_public",
            "released_at",
            "min_android_version",
            "available_platforms",
            "qr_code_url",
            "created_at",
            "updated_at",
        )

    def get_package_url(self, obj: AppRelease) -> str:
        if not obj.package_file:
            return ""
        request = self.context.get("request")
        url = obj.package_file.url
        return request.build_absolute_uri(url) if request else url

    def get_qr_code_url(self, obj: AppRelease) -> str:
        link = obj.resolved_download_url
        if not link:
            return ""
        return f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={quote_plus(link)}"
