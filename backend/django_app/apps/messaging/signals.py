from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .redis_sync import append_message_to_history_cache
from apps.users.push_services import dispatch_message_push


@receiver(post_save, sender=Message)
def message_post_save_sync_history(sender, instance: Message, created: bool, **kwargs):
    if created:
        append_message_to_history_cache(instance)


@receiver(post_save, sender=Message)
def message_post_save_send_push(sender, instance: Message, created: bool, **kwargs):
    if created and not instance.is_deleted:
        dispatch_message_push(instance.id)
