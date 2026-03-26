from django.urls import path

from .views import (
    KnowledgeBaseArticleDetailAPIView,
    KnowledgeBaseArticleListAPIView,
    KnowledgeBaseCategoryListAPIView,
)

urlpatterns = [
    path("knowledge-base/categories/", KnowledgeBaseCategoryListAPIView.as_view(), name="kb-categories"),
    path("knowledge-base/articles/", KnowledgeBaseArticleListAPIView.as_view(), name="kb-articles"),
    path("knowledge-base/articles/<slug:slug>/", KnowledgeBaseArticleDetailAPIView.as_view(), name="kb-article-detail"),
]