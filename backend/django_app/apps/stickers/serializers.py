from rest_framework import serializers

from .models import Sticker, StickerPack


class StickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sticker
        fields = (
            "uuid",
            "title",
            "code",
            "image",
            "emoji",
            "sort_order",
        )


class StickerPackListSerializer(serializers.ModelSerializer):
    stickers_count = serializers.SerializerMethodField()

    class Meta:
        model = StickerPack
        fields = (
            "uuid",
            "title",
            "slug",
            "description",
            "cover",
            "sort_order",
            "is_featured",
            "stickers_count",
        )

    def get_stickers_count(self, obj):
        return obj.stickers.filter(is_active=True).count()


class StickerPackDetailSerializer(serializers.ModelSerializer):
    stickers = serializers.SerializerMethodField()

    class Meta:
        model = StickerPack
        fields = (
            "uuid",
            "title",
            "slug",
            "description",
            "cover",
            "sort_order",
            "is_featured",
            "stickers",
        )

    def get_stickers(self, obj):
        stickers = getattr(obj, "prefetched_active_stickers", None)
        if stickers is None:
            stickers = obj.stickers.filter(is_active=True).order_by("sort_order", "id")
        return StickerSerializer(stickers, many=True).data