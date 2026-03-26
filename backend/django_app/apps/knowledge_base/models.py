from django.db import models

from apps.common.models import UUIDTimeStampedModel


class KnowledgeBaseCategory(UUIDTimeStampedModel):
    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=64, blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "knowledge_base_categories"
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title


class KnowledgeBaseArticle(UUIDTimeStampedModel):
    category = models.ForeignKey(
        "knowledge_base.KnowledgeBaseCategory",
        on_delete=models.CASCADE,
        related_name="articles",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    excerpt = models.TextField(blank=True)
    cover = models.ImageField(upload_to="knowledge-base/covers/", null=True, blank=True)
    content = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "knowledge_base_articles"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.title


class KnowledgeBaseSection(UUIDTimeStampedModel):
    class SectionType(models.TextChoices):
        TEXT = "text", "Text"
        BULLETS = "bullets", "Bullets"
        STEPS = "steps", "Steps"
        FAQ = "faq", "FAQ"
        CALLOUT = "callout", "Callout"

    article = models.ForeignKey(
        "knowledge_base.KnowledgeBaseArticle",
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=180, blank=True)
    section_type = models.CharField(
        max_length=20,
        choices=SectionType.choices,
        default=SectionType.TEXT,
        db_index=True,
    )
    body = models.TextField(blank=True)
    items = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "knowledge_base_sections"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title or f"{self.article.title} / {self.section_type}"