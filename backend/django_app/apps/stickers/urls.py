from django.urls import path

from .views import StickerPackDetailAPIView, StickerPackListAPIView

urlpatterns = [
    path("sticker-packs/", StickerPackListAPIView.as_view(), name="sticker-pack-list"),
    path("sticker-packs/<slug:slug>/", StickerPackDetailAPIView.as_view(), name="sticker-pack-detail"),
]