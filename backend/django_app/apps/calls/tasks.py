import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_call_sessions() -> int:
    from .services import expire_stale_active_calls

    expired_count = expire_stale_active_calls()
    if expired_count:
        logger.info("Expired stale call sessions | count=%s", expired_count)
    return expired_count
