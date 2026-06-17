import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company_name", models.CharField(default="Akyl Cheshmesi", max_length=160)),
                ("legal_company_name", models.CharField(blank=True, max_length=220)),
                ("director_name", models.CharField(default="Алишер Худайбердыев", max_length=160)),
                ("logo", models.FileField(blank=True, null=True, upload_to="website/logos/")),
                ("logo_url", models.URLField(blank=True, max_length=600)),
                ("hero_title", models.CharField(default="Безопасный мессенджер для студентов", max_length=220)),
                ("hero_subtitle", models.TextField(blank=True)),
                ("about_company", models.TextField(blank=True)),
                ("translation_company_text", models.TextField(blank=True)),
                ("students_life_text", models.TextField(blank=True)),
                ("security_text", models.TextField(blank=True)),
                ("privacy_policy", models.TextField(blank=True)),
                ("terms_of_use", models.TextField(blank=True)),
                ("google_play_url", models.URLField(blank=True, max_length=600)),
                ("testflight_url", models.URLField(blank=True, max_length=600)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=80)),
                ("support_email", models.EmailField(blank=True, max_length=254)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
            ],
            options={"db_table": "website_site_settings", "verbose_name": "Настройки сайта", "verbose_name_plural": "Настройки сайта"},
        ),
        migrations.CreateModel(
            name="CompanyTeamMember",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=160)),
                ("role", models.CharField(max_length=160)),
                ("team", models.CharField(choices=[("management", "Руководство"), ("documents", "Перевод документов"), ("students_life", "Student's Life"), ("it", "IT-команда"), ("support", "Поддержка")], db_index=True, default="support", max_length=32)),
                ("bio", models.TextField(blank=True)),
                ("photo", models.FileField(blank=True, null=True, upload_to="website/team/")),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("telegram", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("display_order", models.PositiveIntegerField(db_index=True, default=100)),
            ],
            options={"db_table": "website_team_members", "verbose_name": "Сотрудник / IT-команда", "verbose_name_plural": "Сотрудники и IT-команда", "ordering": ["display_order", "full_name"]},
        ),
        migrations.CreateModel(
            name="SupportRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=160)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=80)),
                ("preferred_contact", models.CharField(blank=True, max_length=80)),
                ("topic", models.CharField(choices=[("admission", "Поступление"), ("document_translation", "Перевод документов"), ("app", "Приложение / мессенджер"), ("partnership", "Партнёрство"), ("support", "Поддержка"), ("other", "Другое")], db_index=True, default="support", max_length=32)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("new", "Новая"), ("in_progress", "В работе"), ("waiting", "Ожидает ответа"), ("resolved", "Решена"), ("spam", "Спам")], db_index=True, default="new", max_length=32)),
                ("source", models.CharField(default="website", max_length=120)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("manager_comment", models.TextField(blank=True)),
            ],
            options={"db_table": "website_support_requests", "verbose_name": "Заявка с сайта", "verbose_name_plural": "Заявки с сайта", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="supportrequest", index=models.Index(fields=["status", "created_at"], name="website_sup_status_1ab9d5_idx")),
        migrations.AddIndex(model_name="supportrequest", index=models.Index(fields=["topic", "created_at"], name="website_sup_topic_71a64b_idx")),
    ]
