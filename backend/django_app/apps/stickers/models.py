from django.db import models

from apps.common.models import UUIDTimeStampedModel


class StickerPack(UUIDTimeStampedModel):
    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="stickers/packs/", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "sticker_packs"
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title


class Sticker(UUIDTimeStampedModel):
    pack = models.ForeignKey(
        "stickers.StickerPack",
        on_delete=models.CASCADE,
        related_name="stickers",
    )
    title = models.CharField(max_length=120)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    image = models.ImageField(upload_to="stickers/items/")
    emoji = models.CharField(max_length=16, blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "stickers"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["pack", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.pack.title} / {self.title}"