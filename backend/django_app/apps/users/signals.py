from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .redis_sync import sync_user_to_redis


@receiver(post_save, sender=User)
def user_post_save_sync(sender, instance: User, **kwargs):
    sync_user_to_redis(instance)