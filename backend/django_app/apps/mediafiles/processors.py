import os
import shutil
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone


@dataclass
class ProcessedImage:
    file: ContentFile
    filename: str
    content_type: str
    size: int
    width: int
    height: int
    thumbnail: ContentFile
    thumbnail_filename: str


def _image_save_kwargs(format_name: str) -> dict:
    quality = max(min(getattr(settings, "IMAGE_UPLOAD_QUALITY", 82), 95), 50)
    if format_name == "WEBP":
        return {"format": "WEBP", "quality": quality, "method": 6}
    return {"format": "JPEG", "quality": quality, "optimize": True, "progressive": True}


def process_image_upload(file_obj) -> ProcessedImage | None:
    from PIL import Image, ImageOps

    original_name = getattr(file_obj, "name", "") or "image"
    content_type = (getattr(file_obj, "content_type", "") or "").lower()

    if content_type == "image/gif" or original_name.lower().endswith(".gif"):
        return None

    file_obj.seek(0)
    image = Image.open(file_obj)
    image = ImageOps.exif_transpose(image)

    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")

    max_size = (
        getattr(settings, "IMAGE_MAX_WIDTH", 1920),
        getattr(settings, "IMAGE_MAX_HEIGHT", 1920),
    )
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    format_name = "WEBP" if image.mode == "RGBA" else "JPEG"
    extension = "webp" if format_name == "WEBP" else "jpg"
    output_content_type = "image/webp" if format_name == "WEBP" else "image/jpeg"

    output = BytesIO()
    save_image = image
    if format_name == "JPEG" and save_image.mode != "RGB":
        save_image = save_image.convert("RGB")
    save_image.save(output, **_image_save_kwargs(format_name))
    output_bytes = output.getvalue()

    thumb = image.copy()
    thumb_size = getattr(settings, "IMAGE_THUMBNAIL_SIZE", 480)
    thumb.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
    thumb_output = BytesIO()
    if thumb.mode != "RGB":
        thumb = thumb.convert("RGB")
    thumb.save(thumb_output, format="WEBP", quality=78, method=6)

    stem = Path(original_name).stem[:80] or "image"
    return ProcessedImage(
        file=ContentFile(output_bytes),
        filename=f"{stem}.{extension}",
        content_type=output_content_type,
        size=len(output_bytes),
        width=save_image.width,
        height=save_image.height,
        thumbnail=ContentFile(thumb_output.getvalue()),
        thumbnail_filename=f"{stem}-thumb.webp",
    )


def make_thumbnail_object_key(user_uuid: str, original_name: str) -> str:
    stem = Path(original_name).stem[:80] or "media"
    return f"uploads/{user_uuid}/thumbs/{uuid4().hex}-{stem}.webp"


def create_video_thumbnail(media) -> str | None:
    from PIL import Image, ImageOps

    if media.storage_provider != media.StorageProvider.LOCAL or not media.file:
        return None

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    try:
        source_path = Path(default_storage.path(media.file.name))
    except Exception:
        return None

    if not source_path.exists():
        return None

    processing_dir = Path(settings.MEDIA_ROOT) / ".processing"
    processing_dir.mkdir(parents=True, exist_ok=True)
    temp_output = processing_dir / f"{uuid4().hex}.jpg"

    command = [
        ffmpeg,
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-vf",
        "scale='min(640,iw)':-2",
        str(temp_output),
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if not temp_output.exists():
            return None

        with temp_output.open("rb") as handle:
            image = Image.open(handle)
            image = ImageOps.exif_transpose(image).convert("RGB")
            thumb_size = getattr(settings, "IMAGE_THUMBNAIL_SIZE", 480)
            image.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format="WEBP", quality=78, method=6)

        key = make_thumbnail_object_key(str(media.owner.uuid), media.original_name)
        saved_name = default_storage.save(key, ContentFile(output.getvalue()))
        media.thumbnail = saved_name
        media.width = media.width or image.width
        media.height = media.height or image.height
        media.processed_at = timezone.now()
        media.save(update_fields=["thumbnail", "width", "height", "processed_at", "updated_at"])
        return saved_name
    except Exception as exc:
        media.processing_error = str(exc)[:1000]
        media.save(update_fields=["processing_error", "updated_at"])
        return None
    finally:
        try:
            os.remove(temp_output)
        except OSError:
            pass
