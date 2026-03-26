from django.apps import AppConfig


class ChatsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chats"
    verbose_name = "Chats"

    def ready(self) -> None:
        from . import signals  # noqa: F401