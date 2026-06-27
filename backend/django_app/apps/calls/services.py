import json
from datetime import timedelta
from typing import Any

import redis
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import CallEvent, CallLog, CallParticipant, CallSession, CallSignal


ACTIVE_CALL_STATUSES = {
    CallSession.Status.REQUESTED,
    CallSession.Status.RINGING,
    CallSession.Status.ACCEPTED,
}
DEFAULT_CALL_MAX_DURATION_SECONDS = 60 * 60


def get_call_max_duration_seconds() -> int:
    configured_value = getattr(
        settings,
        "CALL_MAX_DURATION_SECONDS",
        DEFAULT_CALL_MAX_DURATION_SECONDS,
    )

    try:
        max_duration_seconds = int(configured_value)
    except (TypeError, ValueError):
        return DEFAULT_CALL_MAX_DURATION_SECONDS

    if max_duration_seconds <= 0:
        return DEFAULT_CALL_MAX_DURATION_SECONDS

    return max_duration_seconds


def is_call_session_expired(session: CallSession, now=None) -> bool:
    if session.status not in ACTIVE_CALL_STATUSES:
        return False

    now = now or timezone.now()
    base_time = session.answered_at or session.created_at
    return now - base_time >= timedelta(seconds=get_call_max_duration_seconds())


def expire_stale_active_calls(*, chat=None, session: CallSession | None = None) -> int:
    now = timezone.now()
    cutoff = now - timedelta(seconds=get_call_max_duration_seconds())

    queryset = CallSession.objects.select_related("chat", "initiated_by").prefetch_related(
        "participants",
    )

    if chat is not None:
        queryset = queryset.filter(chat=chat)
    if session is not None:
        queryset = queryset.filter(pk=session.pk)

    queryset = queryset.filter(status__in=ACTIVE_CALL_STATUSES).filter(
        Q(answered_at__isnull=False, answered_at__lte=cutoff)
        | Q(answered_at__isnull=True, created_at__lte=cutoff)
    )

    expired_count = 0
    max_duration_seconds = get_call_max_duration_seconds()

    for stale_session in queryset.iterator():
        previous_status = stale_session.status
        target_status = (
            CallSession.Status.ENDED
            if stale_session.status == CallSession.Status.ACCEPTED
            else CallSession.Status.MISSED
        )
        base_time = stale_session.answered_at or stale_session.created_at
        duration_seconds = max(int((now - base_time).total_seconds()), 0)

        stale_session.status = target_status
        stale_session.ended_at = now
        stale_session.duration_seconds = duration_seconds
        stale_session.save(update_fields=["status", "ended_at", "duration_seconds", "updated_at"])

        for participant in stale_session.participants.all():
            if participant.status == CallParticipant.Status.JOINED:
                if participant.joined_at and not participant.left_at:
                    participant.left_at = now
                    participant.duration_seconds = max(
                        int((now - participant.joined_at).total_seconds()),
                        0,
                    )
                participant.status = CallParticipant.Status.LEFT
                participant.save(update_fields=["status", "left_at", "duration_seconds", "updated_at"])
                continue

            if participant.status in {
                CallParticipant.Status.INVITED,
                CallParticipant.Status.RINGING,
            }:
                participant.status = CallParticipant.Status.MISSED
                participant.left_at = now
                participant.save(update_fields=["status", "left_at", "updated_at"])

        CallLog.objects.create(
            session=stale_session,
            action="call_auto_expired",
            status_from=previous_status,
            status_to=target_status,
            duration_seconds=duration_seconds,
            payload={"max_duration_seconds": max_duration_seconds},
        )
        expired_count += 1

    return expired_count


def ensure_call_session_not_expired(session: CallSession) -> CallSession:
    if is_call_session_expired(session):
        expire_stale_active_calls(session=session)
        session.refresh_from_db()
    return session


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
    CallLog.objects.create(
        session=session,
        actor=actor,
        action=event_type,
        status_to=session.status,
        duration_seconds=session.duration_seconds,
        payload=payload,
    )

    if publish:
        publish_payload = {
            "call_uuid": str(session.uuid),
            "chat_uuid": str(session.chat.uuid),
            "room_key": session.room_key,
            "call_type": session.call_type,
            "status": session.status,
            "initiated_by_uuid": str(session.initiated_by.uuid),
            **payload,
        }
        publish_chat_realtime_event(
            session.chat.uuid,
            event_type,
            publish_payload,
        )

    return event


def create_call_signal(
    *,
    session: CallSession,
    sender,
    signal_type: str,
    payload: dict[str, Any] | None = None,
    target_user=None,
    publish: bool = True,
) -> CallSignal:
    payload = payload or {}
    signal = CallSignal.objects.create(
        session=session,
        sender=sender,
        target_user=target_user,
        signal_type=signal_type,
        payload=payload,
    )

    if publish:
        publish_chat_realtime_event(
            session.chat.uuid,
            f"call:{signal_type}",
            {
                "call_uuid": str(session.uuid),
                "chat_uuid": str(session.chat.uuid),
                "room_key": session.room_key,
                "call_type": session.call_type,
                "status": session.status,
                "initiated_by_uuid": str(session.initiated_by.uuid),
                "sender_uuid": str(sender.uuid),
                "target_user_uuid": str(target_user.uuid) if target_user else "",
                "signal_type": signal_type,
                **payload,
            },
        )

    return signal


def finalize_call_session(session: CallSession, status: str) -> CallSession:
    now = timezone.now()
    base_time = session.answered_at or session.created_at
    duration_seconds = max(int((now - base_time).total_seconds()), 0)

    previous_status = session.status
    session.status = status
    session.ended_at = now
    session.duration_seconds = duration_seconds
    session.save(update_fields=["status", "ended_at", "duration_seconds", "updated_at"])
    CallLog.objects.create(
        session=session,
        action="call_status_changed",
        status_from=previous_status,
        status_to=status,
        duration_seconds=duration_seconds,
        payload={},
    )
    return session


def finalize_participant_if_joined(participant: CallParticipant) -> CallParticipant:
    if participant.joined_at and not participant.left_at:
        now = timezone.now()
        participant.left_at = now
        participant.status = CallParticipant.Status.LEFT
        participant.duration_seconds = max(int((now - participant.joined_at).total_seconds()), 0)
        participant.save(update_fields=["left_at", "status", "duration_seconds", "updated_at"])
    return participant
