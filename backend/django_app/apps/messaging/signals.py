from django.db.models.signals import post_save
from django.db import transaction
from django.dispatch import receiver
import logging

from .models import Message
from .redis_sync import append_message_to_history_cache
from .tasks import send_new_message_push_notifications
from apps.users.push_services import push_is_enabled, send_message_push_by_id

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def message_post_save_sync_history(sender, instance: Message, created: bool, **kwargs):
    if created:
        append_message_to_history_cache(instance)


@receiver(post_save, sender=Message)
def message_post_save_send_push(sender, instance: Message, created: bool, **kwargs):
    if created and not instance.is_deleted:
        if not push_is_enabled():
            return

        def enqueue_push():
            try:
                send_new_message_push_notifications.delay(instance.id)
            except Exception:
                logger.exception("Failed to enqueue message push task; sending synchronously")
                send_message_push_by_id(instance.id)

        transaction.on_commit(enqueue_push)
