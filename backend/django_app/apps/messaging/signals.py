from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .redis_sync import append_message_to_history_cache


@receiver(post_save, sender=Message)
def message_post_save_sync_history(sender, instance: Message, created: bool, **kwargs):
    if created:
        append_message_to_history_cache(instance)