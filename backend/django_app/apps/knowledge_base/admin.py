from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseSection,
)


class KnowledgeBaseSectionInline(TabularInline):
    model = KnowledgeBaseSection
    extra = 0
    fields = ("title", "section_type", "body", "items", "sort_order", "is_active")
    ordering = ("sort_order", "id")
    tab = True


@admin.register(KnowledgeBaseCategory)
class KnowledgeBaseCategoryAdmin(ModelAdmin):
    list_display = ("id", "title", "slug", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(ModelAdmin):
    list_display = (
        "id",
        "title",
        "slug",
        "category",
        "sort_order",
        "is_active",
        "is_featured",
    )
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("title", "slug", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    inlines = [KnowledgeBaseSectionInline]


@admin.register(KnowledgeBaseSection)
class KnowledgeBaseSectionAdmin(ModelAdmin):
    list_display = ("id", "article", "title", "section_type", "sort_order", "is_active")
    list_filter = ("section_type", "is_active")
    search_fields = ("title", "body")
    autocomplete_fields = ("article",)