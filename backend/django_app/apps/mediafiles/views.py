import os
import uuid

from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import UploadedMedia
from .processors import create_video_thumbnail, make_thumbnail_object_key, process_image_upload
from .serializers import (
    LocalMediaUploadSerializer,
    MediaCompleteSerializer,
    MediaPresignRequestSerializer,
    UploadedMediaSerializer,
)
from .validators import validate_upload_input

def validate_media_duration(media_kind: str, duration_seconds: int | None):
    if duration_seconds is None:
        return

    if media_kind == UploadedMedia.MediaKind.VIDEO:
        max_duration = getattr(settings, "VIDEO_NOTE_MAX_DURATION_SECONDS", 60)
        if duration_seconds > max_duration * 10:
            raise ValueError(f"Video duration exceeds {max_duration * 10} seconds")

    if media_kind == UploadedMedia.MediaKind.AUDIO:
        max_duration = getattr(settings, "AUDIO_MAX_DURATION_SECONDS", 300)
        if duration_seconds > max_duration:
            raise ValueError(f"Audio duration exceeds {max_duration} seconds")


def build_s3_client():
    import boto3

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


def build_media_object_key(user_uuid: str, original_name: str) -> str:
    _, ext = os.path.splitext(original_name)
    ext = ext[:12].lower()
    return f"uploads/{user_uuid}/{uuid.uuid4().hex}{ext}"


def build_s3_file_url(bucket_name: str, object_key: str) -> str:
    is_public_read = getattr(settings, "AWS_S3_PUBLIC_READ", False)

    if is_public_read:
        custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "") or ""
        if custom_domain:
            return f"https://{custom_domain.rstrip('/')}/{object_key}"

        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
        endpoint = endpoint.rstrip("/")
        return f"{endpoint}/{bucket_name}/{object_key}"

    s3_client = build_s3_client()
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket_name,
            "Key": object_key,
        },
        ExpiresIn=getattr(settings, "AWS_S3_PRESIGNED_GET_EXPIRES", 3600),
    )


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
                {
                    "detail": "USE_S3 is disabled. Use /api/v1/media/upload-local/.",
                    "storage": "local",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filename = serializer.validated_data["filename"]
        content_type = serializer.validated_data.get("content_type", "").strip()
        size = serializer.validated_data["size"]
        is_public = serializer.validated_data.get("is_public", False)
        duration_seconds = serializer.validated_data.get("duration_seconds")
        width = serializer.validated_data.get("width")
        height = serializer.validated_data.get("height")
        waveform_data = serializer.validated_data.get("waveform_data") or []

        try:
            validated = validate_upload_input(filename, content_type, size)
            validate_media_duration(validated.media_kind, duration_seconds)
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
            is_public=is_public,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            waveform_data=waveform_data,
            meta={
                "duration_seconds": duration_seconds,
                "width": width,
                "height": height,
                "waveform_data": waveform_data,
            },
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
                "media": UploadedMediaSerializer(media, context={"request": request}).data,
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

        if not settings.USE_S3:
            return Response(
                {"detail": "USE_S3 is disabled. This media cannot be completed through S3."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s3_client = build_s3_client()

        try:
            s3_client.head_object(Bucket=media.bucket_name, Key=media.object_key)
        except ClientError as exc:
            media.status = UploadedMedia.Status.FAILED
            media.meta = {
                **media.meta,
                "upload_error": str(exc),
            }
            media.save(update_fields=["status", "meta", "updated_at"])
            return Response(
                {"detail": f"S3 object is not available yet: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        media.status = UploadedMedia.Status.UPLOADED
        media.meta = {
            **media.meta,
            "s3_uploaded": True,
        }
        media.save(update_fields=["status", "meta", "updated_at"])

        return Response(
            UploadedMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class LocalMediaUploadAPIView(generics.GenericAPIView):
    serializer_class = LocalMediaUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "media_upload"

    def post(self, request):
        if settings.USE_S3:
            return Response(
                {
                    "detail": "USE_S3 is enabled. Use /api/v1/media/presign/ instead.",
                    "storage": "s3",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_obj = serializer.validated_data["file"]
        is_public = serializer.validated_data.get("is_public", False)
        duration_seconds = serializer.validated_data.get("duration_seconds")
        width = serializer.validated_data.get("width")
        height = serializer.validated_data.get("height")
        waveform_data = serializer.validated_data.get("waveform_data") or []

        try:
            validated = validate_upload_input(
                file_obj.name,
                getattr(file_obj, "content_type", "") or "",
                file_obj.size,
            )
            validate_media_duration(validated.media_kind, duration_seconds)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        processed_image = None
        if validated.media_kind == UploadedMedia.MediaKind.IMAGE:
            try:
                processed_image = process_image_upload(file_obj)
            except Exception as exc:
                return Response({"detail": f"Image processing failed: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        if processed_image:
            object_key = build_media_object_key(str(request.user.uuid), processed_image.filename)
            saved_name = default_storage.save(object_key, processed_image.file)
            thumbnail_key = make_thumbnail_object_key(str(request.user.uuid), processed_image.thumbnail_filename)
            saved_thumbnail = default_storage.save(thumbnail_key, processed_image.thumbnail)
            file_size = processed_image.size
            content_type = processed_image.content_type
            width = processed_image.width
            height = processed_image.height
            original_name = processed_image.filename
        else:
            file_obj.seek(0)
            object_key = build_media_object_key(str(request.user.uuid), file_obj.name)
            saved_name = default_storage.save(object_key, file_obj)
            saved_thumbnail = ""
            file_size = validated.size
            content_type = validated.content_type
            original_name = file_obj.name

        media = UploadedMedia.objects.create(
            owner=request.user,
            original_name=original_name,
            content_type=content_type,
            size=file_size,
            media_kind=validated.media_kind,
            storage_provider=UploadedMedia.StorageProvider.LOCAL,
            status=UploadedMedia.Status.UPLOADED,
            is_public=is_public,
            object_key=saved_name,
            file=saved_name,
            thumbnail=saved_thumbnail or None,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            waveform_data=waveform_data,
            meta={
                "duration_seconds": duration_seconds,
                "width": width,
                "height": height,
                "waveform_data": waveform_data,
                "optimized": bool(processed_image),
            },
        )

        if media.media_kind == UploadedMedia.MediaKind.VIDEO and not media.thumbnail:
            create_video_thumbnail(media)

        return Response(
            UploadedMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MediaDownloadAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        media = UploadedMedia.objects.filter(
            uuid=kwargs["media_uuid"],
            status=UploadedMedia.Status.UPLOADED,
        ).first()

        if not media:
            return Response({"detail": "Media not found"}, status=status.HTTP_404_NOT_FOUND)

        if media.storage_provider == UploadedMedia.StorageProvider.LOCAL and media.file:
            return Response(
                {
                    "download_url": UploadedMediaSerializer(
                        media,
                        context={"request": request},
                    ).data.get("file_url")
                },
                status=status.HTTP_200_OK,
            )

        if media.storage_provider == UploadedMedia.StorageProvider.S3:
            if not settings.USE_S3:
                return Response(
                    {"detail": "USE_S3 is disabled. Download URL is not available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                return Response(
                    {"download_url": build_s3_file_url(media.bucket_name, media.object_key)},
                    status=status.HTTP_200_OK,
                )
            except Exception:
                return Response({"detail": "Failed to build download URL"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Download is not available"}, status=status.HTTP_400_BAD_REQUEST)
