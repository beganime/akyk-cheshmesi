from rest_framework import serializers

from .models import UploadedMedia


class UploadedMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedMedia
        fields = (
            "uuid",
            "original_name",
            "content_type",
            "size",
            "media_kind",
            "storage_provider",
            "object_key",
            "status",
            "is_public",
            "file_url",
            "meta",
            "created_at",
            "updated_at",
        )

    def get_file_url(self, obj):
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return obj.meta.get("file_url")


class MediaAttachmentBriefSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedMedia
        fields = (
            "uuid",
            "original_name",
            "content_type",
            "size",
            "media_kind",
            "file_url",
        )

    def get_file_url(self, obj):
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return obj.meta.get("file_url")


class MediaPresignRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    size = serializers.IntegerField(min_value=1)


class MediaCompleteSerializer(serializers.Serializer):
    media_uuid = serializers.UUIDField()


class LocalMediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    is_public = serializers.BooleanField(required=False, default=False)

    def validate_file(self, value):
        if value.size <= 0:
            raise serializers.ValidationError("Empty file is not allowed")
        return value