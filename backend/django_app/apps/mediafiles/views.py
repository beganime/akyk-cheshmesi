import os
import uuid

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import UploadedMedia
from .serializers import (
    LocalMediaUploadSerializer,
    MediaCompleteSerializer,
    MediaPresignRequestSerializer,
    UploadedMediaSerializer,
)
from .validators import validate_upload_input


def build_s3_client():
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None) or None,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
        config=BotoConfig(signature_version="s3v4"),
    )


def build_media_object_key(user_uuid: str, original_name: str) -> str:
    _, ext = os.path.splitext(original_name)
    ext = ext[:12]
    return f"uploads/{user_uuid}/{uuid.uuid4().hex}{ext}"


def build_s3_file_url(bucket_name: str, object_key: str) -> str:
    custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "") or ""
    if custom_domain:
        return f"https://{custom_domain.rstrip('/')}/{object_key}"

    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
    endpoint = endpoint.rstrip("/")
    return f"{endpoint}/{bucket_name}/{object_key}"


class MyUploadedMediaListAPIView(generics.ListAPIView):
    serializer_class = UploadedMediaSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "media_list"

    def get_queryset(self):
        return UploadedMedia.objects.filter(owner=self.request.user).order_by("-created_at")


class MediaPresignAPIView(generics.GenericAPIView):
    serializer_class = MediaPresignRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "media_presign"

    def post(self, request):
        if not settings.USE_S3:
            return Response(
                {"detail": "USE_S3 is disabled. Use /api/v1/media/upload-local/ in local development."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filename = serializer.validated_data["filename"]
        content_type = serializer.validated_data.get("content_type", "").strip()
        size = serializer.validated_data["size"]

        try:
            validated = validate_upload_input(filename, content_type, size)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        object_key = build_media_object_key(str(request.user.uuid), filename)

        media = UploadedMedia.objects.create(
            owner=request.user,
            original_name=filename,
            content_type=validated.content_type,
            size=validated.size,
            media_kind=validated.media_kind,
            storage_provider=UploadedMedia.StorageProvider.S3,
            object_key=object_key,
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            status=UploadedMedia.Status.PENDING,
        )

        s3_client = build_s3_client()
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": object_key,
                "ContentType": validated.content_type,
            },
            ExpiresIn=900,
        )

        return Response(
            {
                "media": UploadedMediaSerializer(media).data,
                "upload": {
                    "method": "PUT",
                    "url": upload_url,
                    "headers": {
                        "Content-Type": validated.content_type,
                    },
                    "expires_in_seconds": 900,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MediaCompleteAPIView(generics.GenericAPIView):
    serializer_class = MediaCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "media_complete"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        media = UploadedMedia.objects.filter(
            uuid=serializer.validated_data["media_uuid"],
            owner=request.user,
        ).first()

        if not media:
            return Response({"detail": "Media not found"}, status=status.HTTP_404_NOT_FOUND)

        if media.storage_provider != UploadedMedia.StorageProvider.S3:
            return Response(
                {"detail": "Only S3 pending uploads use this endpoint"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s3_client = build_s3_client()

        try:
            s3_client.head_object(Bucket=media.bucket_name, Key=media.object_key)
        except ClientError as exc:
            return Response(
                {"detail": f"S3 object is not available yet: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        media.status = UploadedMedia.Status.UPLOADED
        media.meta = {
            **media.meta,
            "file_url": build_s3_file_url(media.bucket_name, media.object_key),
        }
        media.save(update_fields=["status", "meta", "updated_at"])

        return Response(UploadedMediaSerializer(media).data, status=status.HTTP_200_OK)


class LocalMediaUploadAPIView(generics.GenericAPIView):
    serializer_class = LocalMediaUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "media_upload"

    def post(self, request):
        if settings.USE_S3:
            return Response(
                {"detail": "USE_S3 is enabled. Use /api/v1/media/presign/ instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_obj = serializer.validated_data["file"]
        is_public = serializer.validated_data.get("is_public", False)

        try:
            validated = validate_upload_input(
                file_obj.name,
                getattr(file_obj, "content_type", "") or "",
                file_obj.size,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        media = UploadedMedia.objects.create(
            owner=request.user,
            original_name=file_obj.name,
            content_type=validated.content_type,
            size=validated.size,
            media_kind=validated.media_kind,
            storage_provider=UploadedMedia.StorageProvider.LOCAL,
            status=UploadedMedia.Status.UPLOADED,
            is_public=is_public,
            object_key=build_media_object_key(str(request.user.uuid), file_obj.name),
            file=file_obj,
        )

        return Response(UploadedMediaSerializer(media).data, status=status.HTTP_201_CREATED)