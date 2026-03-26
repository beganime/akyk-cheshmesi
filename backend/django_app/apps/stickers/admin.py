from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Sticker, StickerPack


class StickerInline(TabularInline):
    model = Sticker
    extra = 0
    fields = ("title", "code", "image", "emoji", "sort_order", "is_active")
    ordering = ("sort_order", "id")
    tab = True


@admin.register(StickerPack)
class StickerPackAdmin(ModelAdmin):
    list_display = ("id", "title", "slug", "sort_order", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured")
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [StickerInline]


@admin.register(Sticker)
class StickerAdmin(ModelAdmin):
    list_display = ("id", "title", "code", "pack", "emoji", "sort_order", "is_active")
    list_filter = ("is_active", "pack")
    search_fields = ("title", "code", "emoji")
    autocomplete_fields = ("pack",)