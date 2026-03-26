from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Chat, ChatMember
from .redis_sync import (
    remove_chat_from_redis,
    remove_chat_member_from_redis,
    sync_chat_member_to_redis,
    sync_chat_to_redis,
)


@receiver(post_save, sender=Chat)
def chat_post_save_sync(sender, instance: Chat, **kwargs):
    sync_chat_to_redis(instance)


@receiver(post_delete, sender=Chat)
def chat_post_delete_cleanup(sender, instance: Chat, **kwargs):
    remove_chat_from_redis(instance.uuid)


@receiver(post_save, sender=ChatMember)
def chat_member_post_save_sync(sender, instance: ChatMember, **kwargs):
    sync_chat_member_to_redis(instance)
    sync_chat_to_redis(instance.chat)


@receiver(post_delete, sender=ChatMember)
def chat_member_post_delete_cleanup(sender, instance: ChatMember, **kwargs):
    remove_chat_member_from_redis(instance.chat.uuid, instance.user.uuid)
    sync_chat_to_redis(instance.chat)