from django.conf import settings
from rest_framework import serializers

from .models import UploadedMedia


def build_s3_client():
    import boto3
    from botocore.client import Config as BotoConfig

    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None) or None,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def get_s3_file_url(obj) -> str | None:
    if not obj.bucket_name or not obj.object_key:
        return None

    is_public_read = getattr(settings, "AWS_S3_PUBLIC_READ", False)

    if is_public_read:
        custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "") or ""
        if custom_domain:
            return f"https://{custom_domain.rstrip('/')}/{obj.object_key}"

        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
        endpoint = endpoint.rstrip("/")
        return f"{endpoint}/{obj.bucket_name}/{obj.object_key}"

    s3_client = build_s3_client()
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": obj.bucket_name,
            "Key": obj.object_key,
        },
        ExpiresIn=getattr(settings, "AWS_S3_PRESIGNED_GET_EXPIRES", 3600),
    )


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

        if obj.storage_provider == UploadedMedia.StorageProvider.S3 and obj.status == UploadedMedia.Status.UPLOADED:
            try:
                return get_s3_file_url(obj)
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

        if obj.storage_provider == UploadedMedia.StorageProvider.S3 and obj.status == UploadedMedia.Status.UPLOADED:
            try:
                return get_s3_file_url(obj)
            except Exception:
                return None

        return obj.meta.get("file_url")


class MediaPresignRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    size = serializers.IntegerField(min_value=1)
    is_public = serializers.BooleanField(required=False, default=False)
    duration_seconds = serializers.IntegerField(required=False, min_value=1)


class MediaCompleteSerializer(serializers.Serializer):
    media_uuid = serializers.UUIDField()


class LocalMediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    is_public = serializers.BooleanField(required=False, default=False)
    duration_seconds = serializers.IntegerField(required=False, min_value=1)

    def validate_file(self, value):
        if value.size <= 0:
            raise serializers.ValidationError("Empty file is not allowed")
        return value
