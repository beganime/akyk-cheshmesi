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
