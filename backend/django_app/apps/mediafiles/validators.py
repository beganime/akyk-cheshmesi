import mimetypes
import os
from dataclasses import dataclass

from django.conf import settings


@dataclass
class ValidatedMediaMeta:
    content_type: str
    media_kind: str
    size: int


def detect_media_kind(content_type: str) -> str:
    content_type = (content_type or "").lower()

    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    return "file"


def normalize_content_type(filename: str, content_type: str) -> str:
    content_type = (content_type or "").strip().lower()
    if content_type:
        return content_type

    guessed, _ = mimetypes.guess_type(filename)
    return (guessed or "application/octet-stream").lower()


def validate_upload_input(filename: str, content_type: str, size: int) -> ValidatedMediaMeta:
    max_size = getattr(settings, "MEDIA_MAX_UPLOAD_SIZE_BYTES", 25 * 1024 * 1024)
    if size <= 0:
        raise ValueError("Empty file is not allowed")

    if size > max_size:
        raise ValueError(f"File is too large. Max size is {max_size} bytes")

    normalized_content_type = normalize_content_type(filename, content_type)
    allowed = set(getattr(settings, "MEDIA_ALLOWED_CONTENT_TYPES", []))
    extension = os.path.splitext(filename or "")[1].lower().lstrip(".")
    allowed_extensions = set(getattr(settings, "MEDIA_ALLOWED_EXTENSIONS", []))
    blocked_extensions = set(getattr(settings, "MEDIA_BLOCKED_EXTENSIONS", []))

    if not extension:
        raise ValueError("File extension is required")

    if extension in blocked_extensions:
        raise ValueError(f"File extension is not allowed: .{extension}")

    if allowed_extensions and extension not in allowed_extensions:
        raise ValueError(f"Unsupported file extension: .{extension}")

    if allowed and normalized_content_type not in allowed:
        raise ValueError(f"Unsupported content type: {normalized_content_type}")

    media_kind = detect_media_kind(normalized_content_type)

    if media_kind == "video":
        max_size = getattr(settings, "VIDEO_MAX_SIZE_MB", 100) * 1024 * 1024
    elif media_kind == "audio":
        max_size = getattr(settings, "AUDIO_MAX_SIZE_MB", 25) * 1024 * 1024

    if size > max_size:
        raise ValueError(f"File is too large for {media_kind}. Max size is {max_size} bytes")

    return ValidatedMediaMeta(
        content_type=normalized_content_type,
        media_kind=media_kind,
        size=size,
    )
