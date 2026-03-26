from rest_framework import serializers

from .models import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseSection,
)


class KnowledgeBaseSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBaseSection
        fields = (
            "uuid",
            "title",
            "section_type",
            "body",
            "items",
            "sort_order",
        )


class KnowledgeBaseArticleListSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = KnowledgeBaseArticle
        fields = (
            "uuid",
            "title",
            "slug",
            "excerpt",
            "cover",
            "category",
            "is_featured",
            "sort_order",
            "created_at",
            "updated_at",
        )


class KnowledgeBaseArticleDetailSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeBaseArticle
        fields = (
            "uuid",
            "title",
            "slug",
            "excerpt",
            "cover",
            "content",
            "category",
            "is_featured",
            "sort_order",
            "sections",
            "created_at",
            "updated_at",
        )

    def get_category(self, obj):
        return {
            "uuid": str(obj.category.uuid),
            "title": obj.category.title,
            "slug": obj.category.slug,
            "icon": obj.category.icon,
        }

    def get_sections(self, obj):
        sections = getattr(obj, "prefetched_active_sections", None)
        if sections is None:
            sections = obj.sections.filter(is_active=True).order_by("sort_order", "id")
        return KnowledgeBaseSectionSerializer(sections, many=True).data


class KnowledgeBaseCategorySerializer(serializers.ModelSerializer):
    articles_count = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeBaseCategory
        fields = (
            "uuid",
            "title",
            "slug",
            "description",
            "icon",
            "sort_order",
            "articles_count",
        )

    def get_articles_count(self, obj):
        return obj.articles.filter(is_active=True).count()