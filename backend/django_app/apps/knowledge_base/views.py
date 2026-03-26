from django.db.models import Prefetch
from rest_framework import generics, permissions

from .models import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseSection,
)
from .serializers import (
    KnowledgeBaseArticleDetailSerializer,
    KnowledgeBaseArticleListSerializer,
    KnowledgeBaseCategorySerializer,
)


class KnowledgeBaseCategoryListAPIView(generics.ListAPIView):
    serializer_class = KnowledgeBaseCategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return KnowledgeBaseCategory.objects.filter(is_active=True).order_by("sort_order", "title")


class KnowledgeBaseArticleListAPIView(generics.ListAPIView):
    serializer_class = KnowledgeBaseArticleListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = (
            KnowledgeBaseArticle.objects.filter(
                is_active=True,
                category__is_active=True,
            )
            .select_related("category")
            .order_by("sort_order", "title")
        )

        category_slug = (self.request.query_params.get("category") or "").strip()
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        featured = (self.request.query_params.get("featured") or "").strip().lower()
        if featured in {"1", "true", "yes"}:
            queryset = queryset.filter(is_featured=True)

        return queryset


class KnowledgeBaseArticleDetailAPIView(generics.RetrieveAPIView):
    serializer_class = KnowledgeBaseArticleDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return (
            KnowledgeBaseArticle.objects.filter(
                is_active=True,
                category__is_active=True,
            )
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "sections",
                    queryset=KnowledgeBaseSection.objects.filter(is_active=True).order_by("sort_order", "id"),
                    to_attr="prefetched_active_sections",
                )
            )
        )