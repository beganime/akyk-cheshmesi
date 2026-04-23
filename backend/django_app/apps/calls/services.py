import json
from typing import Any

import redis
from django.conf import settings
from django.utils import timezone

from .models import CallEvent, CallParticipant, CallSession


ACTIVE_CALL_STATUSES = {
    CallSession.Status.REQUESTED,
    CallSession.Status.RINGING,
    CallSession.Status.ACCEPTED,
}


def get_realtime_redis_url() -> str:
    cache_location = settings.CACHES.get("default", {}).get("LOCATION")
    if isinstance(cache_location, (list, tuple)):
        cache_location = cache_location[0] if cache_location else None

    if cache_location:
        return str(cache_location)

    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    if broker_url:
        return str(broker_url)

    return "redis://127.0.0.1:6379/0"


def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(get_realtime_redis_url(), decode_responses=True)


def publish_chat_realtime_event(chat_uuid, event_type: str, payload: dict[str, Any] | None = None) -> bool:
    envelope = {
        "type": event_type,
        "chat_uuid": str(chat_uuid),
        "payload": payload or {},
    }

    try:
        client = get_redis_client()
        client.publish(
            settings.REDIS_REALTIME_EVENTS_CHANNEL,
            json.dumps(envelope, default=str),
        )
        return True
    except Exception:
        return False


def create_call_event(
    session: CallSession,
    event_type: str,
    actor=None,
    payload: dict[str, Any] | None = None,
    publish: bool = True,
) -> CallEvent:
    payload = payload or {}

    event = CallEvent.objects.create(
        session=session,
        actor=actor,
        event_type=event_type,
        payload=payload,
    )

    if publish:
        publish_payload = {
            "call_uuid": str(session.uuid),
            "chat_uuid": str(session.chat.uuid),
            "room_key": session.room_key,
            "call_type": session.call_type,
            "status": session.status,
            **payload,
        }
        publish_chat_realtime_event(
            session.chat.uuid,
            event_type,
            publish_payload,
        )

    return event


def finalize_call_session(session: CallSession, status: str) -> CallSession:
    now = timezone.now()
    base_time = session.answered_at or session.created_at
    duration_seconds = max(int((now - base_time).total_seconds()), 0)

    session.status = status
    session.ended_at = now
    session.duration_seconds = duration_seconds
    session.save(update_fields=["status", "ended_at", "duration_seconds", "updated_at"])
    return session


def finalize_participant_if_joined(participant: CallParticipant) -> CallParticipant:
    if participant.joined_at and not participant.left_at:
        now = timezone.now()
        participant.left_at = now
        participant.status = CallParticipant.Status.LEFT
        participant.duration_seconds = max(int((now - participant.joined_at).total_seconds()), 0)
        participant.save(update_fields=["left_at", "status", "duration_seconds", "updated_at"])
    return participant