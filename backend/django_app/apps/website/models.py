from django.db import models

from apps.common.models import UUIDTimeStampedModel


class SiteSettings(UUIDTimeStampedModel):
    class Meta:
        db_table = "website_site_settings"
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    company_name = models.CharField(max_length=160, default="Akyl Cheshmesi")
    legal_company_name = models.CharField(max_length=220, blank=True)
    director_name = models.CharField(max_length=160, default="Алишер Худайбердыев")
    logo = models.FileField(upload_to="website/logos/", blank=True, null=True)
    logo_url = models.URLField(max_length=600, blank=True)
    hero_title = models.CharField(max_length=220, default="Безопасный мессенджер для студентов")
    hero_subtitle = models.TextField(blank=True)
    about_company = models.TextField(blank=True)
    translation_company_text = models.TextField(blank=True)
    students_life_text = models.TextField(blank=True)
    security_text = models.TextField(blank=True)
    privacy_policy = models.TextField(blank=True)
    terms_of_use = models.TextField(blank=True)
    google_play_url = models.URLField(max_length=600, blank=True)
    testflight_url = models.URLField(max_length=600, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=80, blank=True)
    support_email = models.EmailField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)

    def __str__(self) -> str:
        return self.company_name


class CompanyTeamMember(UUIDTimeStampedModel):
    class Team(models.TextChoices):
        MANAGEMENT = "management", "Руководство"
        DOCUMENTS = "documents", "Перевод документов"
        STUDENTS_LIFE = "students_life", "Student's Life"
        IT = "it", "IT-команда"
        SUPPORT = "support", "Поддержка"

    full_name = models.CharField(max_length=160)
    role = models.CharField(max_length=160)
    team = models.CharField(max_length=32, choices=Team.choices, default=Team.SUPPORT, db_index=True)
    bio = models.TextField(blank=True)
    photo = models.FileField(upload_to="website/team/", blank=True, null=True)
    email = models.EmailField(blank=True)
    telegram = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=100, db_index=True)

    class Meta:
        db_table = "website_team_members"
        ordering = ["display_order", "full_name"]
        verbose_name = "Сотрудник / IT-команда"
        verbose_name_plural = "Сотрудники и IT-команда"

    def __str__(self) -> str:
        return f"{self.full_name} — {self.role}"


class SupportRequest(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        WAITING = "waiting", "Ожидает ответа"
        RESOLVED = "resolved", "Решена"
        SPAM = "spam", "Спам"

    class Topic(models.TextChoices):
        ADMISSION = "admission", "Поступление"
        DOCUMENT_TRANSLATION = "document_translation", "Перевод документов"
        APP = "app", "Приложение / мессенджер"
        PARTNERSHIP = "partnership", "Партнёрство"
        SUPPORT = "support", "Поддержка"
        OTHER = "other", "Другое"

    full_name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=80, blank=True)
    preferred_contact = models.CharField(max_length=80, blank=True)
    topic = models.CharField(max_length=32, choices=Topic.choices, default=Topic.SUPPORT, db_index=True)
    message = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW, db_index=True)
    source = models.CharField(max_length=120, default="website")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    manager_comment = models.TextField(blank=True)

    class Meta:
        db_table = "website_support_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["topic", "created_at"]),
        ]
        verbose_name = "Заявка с сайта"
        verbose_name_plural = "Заявки с сайта"

    def __str__(self) -> str:
        return f"{self.full_name} — {self.get_topic_display()}"
