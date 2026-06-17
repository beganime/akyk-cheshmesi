from django.db import migrations


def seed_default_content(apps, schema_editor):
    SiteSettings = apps.get_model("website", "SiteSettings")
    CompanyTeamMember = apps.get_model("website", "CompanyTeamMember")

    SiteSettings.objects.get_or_create(
        company_name="Akyl Cheshmesi",
        defaults={
            "legal_company_name": "Akyl Cheshmesi",
            "director_name": "Алишер Худайбердыев",
            "hero_title": "Безопасный мессенджер для студентов, документов и образовательного сопровождения",
            "hero_subtitle": "Akyl Cheshmesi объединяет команду переводов документов, Student's Life, кураторов и IT‑поддержку в одном удобном пространстве для студентов.",
            "about_company": "Проект создан для студентов: от подготовки документов до поступления, визы, переезда и адаптации.",
            "translation_company_text": "Команда переводов помогает готовить, проверять и сопровождать документы.",
            "students_life_text": "Student's Life помогает студентам с выбором страны и университета, поступлением, визовыми этапами, жильём и адаптацией.",
            "security_text": "Мы используем контроль доступа к чатам, токены для API, ограничения загрузок и безопасное хранение файлов.",
            "privacy_policy": "Akyl Cheshmesi обрабатывает данные аккаунта, сообщения, медиа, звонки, stories, заявки и технические события для работы сервиса, безопасности и поддержки студентов. Мы не продаём персональные данные.",
            "terms_of_use": "Akyl Cheshmesi предназначен для общения студентов, менеджеров, переводчиков документов, кураторов и IT‑поддержки. Пользователь отвечает за свои данные, аккаунт и материалы, которые отправляет.",
            "is_published": True,
        },
    )

    CompanyTeamMember.objects.get_or_create(
        full_name="Алишер Худайбердыев",
        defaults={
            "role": "Гендиректор",
            "team": "management",
            "bio": "Руководитель проекта Akyl Cheshmesi.",
            "display_order": 1,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [("website", "0001_initial")]

    operations = [migrations.RunPython(seed_default_content, migrations.RunPython.noop)]
