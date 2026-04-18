from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


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
        verify=getattr(settings, "AWS_S3_VERIFY", None),
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def make_absolute_media_url(url: str | None) -> str | None:
    if not url:
        return None

    if url.startswith("http://") or url.startswith("https://"):
        return url

    base_url = getattr(settings, "PUBLIC_MEDIA_BASE_URL", "") or ""
    base_url = base_url.rstrip("/")

    if base_url:
        if not url.startswith("/"):
            url = f"/{url}"
        return f"{base_url}{url}"

    return url


def build_private_file_url(file_field) -> str | None:
    if not file_field:
        return None

    name = getattr(file_field, "name", "") or ""
    if not name:
        return None

    use_s3 = bool(getattr(settings, "USE_S3", False))
    is_public_read = bool(getattr(settings, "AWS_S3_PUBLIC_READ", False))

    if use_s3 and not is_public_read:
        try:
            s3_client = build_s3_client()
            return s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": name,
                },
                ExpiresIn=getattr(settings, "AWS_S3_PRESIGNED_GET_EXPIRES", 3600),
            )
        except Exception:
            pass

    try:
        return make_absolute_media_url(file_field.url)
    except Exception:
        try:
            return make_absolute_media_url(file_field.storage.url(name))
        except Exception:
            return None


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["avatar"] = build_private_file_url(getattr(instance, "avatar", None))
        return data