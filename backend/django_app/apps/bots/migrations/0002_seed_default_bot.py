from django.db import migrations


def seed_default_bot(apps, schema_editor):
    BotProfile = apps.get_model("bots", "BotProfile")
    BotCommand = apps.get_model("bots", "BotCommand")

    bot, _ = BotProfile.objects.get_or_create(
        code="akyl_assistant",
        defaults={
            "title": "Akyl Assistant",
            "description": "Бот по умолчанию для помощи пользователям. Можно редактировать через Django admin.",
            "is_active": True,
        },
    )

    defaults = [
        ("/start", "Привет! Я бот Akyl Assistant. Напиши /help, чтобы посмотреть доступные команды."),
        ("/help", "Доступные команды: /start, /help, /about"),
        ("/about", "Akyl Assistant настроен через Django admin и может быть изменён без обновления приложения."),
    ]

    for command, response_text in defaults:
        BotCommand.objects.get_or_create(
            bot=bot,
            command=command,
            defaults={
                "response_text": response_text,
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("bots", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_bot, noop),
    ]
