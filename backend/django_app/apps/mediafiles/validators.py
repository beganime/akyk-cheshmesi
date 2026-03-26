import mimetypes
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

    if allowed and normalized_content_type not in allowed:
        raise ValueError(f"Unsupported content type: {normalized_content_type}")

    return ValidatedMediaMeta(
        content_type=normalized_content_type,
        media_kind=detect_media_kind(normalized_content_type),
        size=size,
    )