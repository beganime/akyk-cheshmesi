from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_new_message_push_notifications(message_id: int) -> dict:
    from apps.users.push_services import send_message_push_by_id

    result = send_message_push_by_id(message_id)
    logger.info(
        "Message push task finished | message_id=%s attempted=%s sent=%s skipped=%s disabled=%s",
        message_id,
        result.attempted_count,
        result.sent_count,
        result.skipped_count,
        result.disabled,
    )
    return result.as_dict()


@shared_task(name="apps.messaging.tasks.enforce_support_chat_retention")
def enforce_support_chat_retention() -> dict:
    from datetime import timedelta

    from django.conf import settings
    from django.db import transaction
    from django.utils import timezone

    from apps.chats.models import Chat
    from apps.mediafiles.models import UploadedMedia
    from apps.messaging.models import Message, MessageReceipt
    from apps.users.models import User

    if not settings.CHAT_RETENTION_ENABLED:
        return {"status": "disabled", "warned": 0, "postponed": 0, "deleted": 0}

    now = timezone.now()
    cutoff = now - timedelta(days=max(settings.CHAT_RETENTION_DAYS, 1))
    grace = timedelta(days=max(settings.CHAT_RETENTION_GRACE_DAYS, 1))
    support = User.objects.filter(username="sl-support", is_active=True).first()
    stats = {"status": "ok", "warned": 0, "postponed": 0, "deleted": 0}

    chats = Chat.objects.filter(direct_key__startswith="sl-support:", is_active=True).order_by("pk")
    for chat in chats.iterator():
        if chat.retention_warned_at:
            has_response = chat.messages.filter(
                created_at__gt=chat.retention_warned_at,
                is_deleted=False,
            ).exclude(metadata__retention_warning=True).exists()
            if has_response:
                chat.retention_warned_at = None
                chat.retention_delete_after = None
                chat.save(update_fields=["retention_warned_at", "retention_delete_after", "updated_at"])
                stats["postponed"] += 1
                continue
            if chat.retention_delete_after and chat.retention_delete_after <= now:
                attachments = list(
                    UploadedMedia.objects.filter(message_attachments__message__chat=chat).distinct()
                )
                with transaction.atomic():
                    chat.messages.all().delete()
                    chat.last_message_at = now
                    chat.retention_warned_at = None
                    chat.retention_delete_after = None
                    chat.save(update_fields=[
                        "last_message_at", "retention_warned_at", "retention_delete_after", "updated_at",
                    ])
                for media in attachments:
                    if media.message_attachments.exists():
                        continue
                    if media.file:
                        media.file.delete(save=False)
                    if media.thumbnail:
                        media.thumbnail.delete(save=False)
                    media.delete()
                stats["deleted"] += 1
                continue

        activity_at = chat.last_message_at or chat.created_at
        if activity_at > cutoff or not support:
            continue

        with transaction.atomic():
            warning = Message.objects.create(
                chat=chat,
                sender=support,
                message_type=Message.MessageType.SYSTEM,
                text=(
                    "Переписка не использовалась 3 месяца. Через 3 дня история и вложения будут удалены. "
                    "Ответьте в чат, если переписку нужно сохранить."
                ),
                metadata={"retention_warning": True},
            )
            recipient_ids = list(
                chat.members.filter(is_active=True).exclude(user=support).values_list("user_id", flat=True)
            )
            MessageReceipt.objects.bulk_create(
                [MessageReceipt(message=warning, user_id=user_id) for user_id in recipient_ids],
                ignore_conflicts=True,
            )
            chat.last_message_at = warning.created_at
            chat.retention_warned_at = warning.created_at
            chat.retention_delete_after = now + grace
            chat.save(update_fields=[
                "last_message_at", "retention_warned_at", "retention_delete_after", "updated_at",
            ])
        send_new_message_push_notifications.delay(warning.pk)
        stats["warned"] += 1

    return stats
