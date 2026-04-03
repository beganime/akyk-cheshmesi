from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .redis_sync import append_message_to_history_cache
from .tasks import send_new_message_push_notifications


@receiver(post_save, sender=Message)
def message_post_save_sync_history(sender, instance: Message, created: bool, **kwargs):
    if created:
        append_message_to_history_cache(instance)


@receiver(post_save, sender=Message)
def message_post_save_send_push(sender, instance: Message, created: bool, **kwargs):
    if created and not instance.is_deleted:
        send_new_message_push_notifications.delay(instance.id)