from django.db.models import Prefetch
from rest_framework import generics, permissions

from .models import Sticker, StickerPack
from .serializers import StickerPackDetailSerializer, StickerPackListSerializer


class StickerPackListAPIView(generics.ListAPIView):
    serializer_class = StickerPackListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = StickerPack.objects.filter(is_active=True).order_by("sort_order", "title")

        featured = (self.request.query_params.get("featured") or "").strip().lower()
        if featured in {"1", "true", "yes"}:
            queryset = queryset.filter(is_featured=True)

        return queryset


class StickerPackDetailAPIView(generics.RetrieveAPIView):
    serializer_class = StickerPackDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return StickerPack.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "stickers",
                queryset=Sticker.objects.filter(is_active=True).order_by("sort_order", "id"),
                to_attr="prefetched_active_stickers",
            )
        )