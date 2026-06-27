import json
from datetime import timedelta
from typing import Any

import redis
from django.conf import settings
from django.utils import timezone

from .models import CallEvent, CallLog, CallParticipant, CallSession, CallSignal


ACTIVE_CALL_STATUSES = {
    CallSession.Status.REQUESTED,
    CallSession.Status.RINGING,
    CallSession.Status.ACCEPTED,
}

CALL_MAX_DURATION_SECONDS = int(getattr(settings, "CALL_MAX_DURATION_SECONDS", 60 * 60))
CALL_PENDING_TIMEOUT_SECONDS = int(getattr(settings, "CALL_PENDING_TIMEOUT_SECONDS", 2 * 60))


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


def _call_duration_seconds(session: CallSession, ended_at=None) -> int:
    finished_at = ended_at or timezone.now()
    base_time = session.answered_at or session.created_at
    return max(int((finished_at - base_time).total_seconds()), 0)


def finalize_call_session(session: CallSession, status: str, ended_at=None) -> CallSession:
    now = ended_at or timezone.now()
    duration_seconds = _call_duration_seconds(session, now)

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


def finalize_participant_if_joined(participant: CallParticipant, left_at=None) -> CallParticipant:
    if participant.joined_at and not participant.left_at:
        now = left_at or timezone.now()
        participant.left_at = now
        participant.status = CallParticipant.Status.LEFT
        participant.duration_seconds = max(int((now - participant.joined_at).total_seconds()), 0)
        participant.save(update_fields=["left_at", "status", "duration_seconds", "updated_at"])
    return participant


def _finish_expired_session(session: CallSession, status: str, ended_at) -> None:
    session = finalize_call_session(session, status, ended_at=ended_at)

    for participant in session.participants.all():
        if participant.status == CallParticipant.Status.JOINED:
            finalize_participant_if_joined(participant, left_at=ended_at)
        elif participant.status in {
            CallParticipant.Status.INVITED,
            CallParticipant.Status.RINGING,
        }:
            participant.status = CallParticipant.Status.MISSED
            participant.left_at = ended_at
            participant.save(update_fields=["status", "left_at", "updated_at"])

    create_call_event(
        session=session,
        event_type="call:auto-end",
        actor=None,
        payload={
            "reason": "expired",
            "max_duration_seconds": CALL_MAX_DURATION_SECONDS,
            "pending_timeout_seconds": CALL_PENDING_TIMEOUT_SECONDS,
        },
        publish=True,
    )


def expire_stale_active_calls(*, chat=None, user=None, now=None) -> int:
    """Close stale call sessions before they block new calls or stay open forever.

    Accepted calls are limited to CALL_MAX_DURATION_SECONDS (default: 1 hour).
    Pending/ringing calls are closed after CALL_PENDING_TIMEOUT_SECONDS (default: 2 minutes).
    """
    current_time = now or timezone.now()
    expired_count = 0

    active_queryset = CallSession.objects.select_related("chat", "initiated_by").prefetch_related("participants")
    if chat is not None:
        active_queryset = active_queryset.filter(chat=chat)
    if user is not None:
        active_queryset = active_queryset.filter(participants__user=user)

    accepted_cutoff = current_time - timedelta(seconds=CALL_MAX_DURATION_SECONDS)
    accepted_sessions = (
        active_queryset.filter(
            status=CallSession.Status.ACCEPTED,
            answered_at__isnull=False,
            answered_at__lte=accepted_cutoff,
            ended_at__isnull=True,
        )
        .distinct()
        .order_by("created_at")
    )

    for session in accepted_sessions:
        expire_at = session.answered_at + timedelta(seconds=CALL_MAX_DURATION_SECONDS)
        _finish_expired_session(session, CallSession.Status.ENDED, expire_at)
        expired_count += 1

    stuck_accepted_sessions = (
        active_queryset.filter(
            status=CallSession.Status.ACCEPTED,
            answered_at__isnull=True,
            created_at__lte=accepted_cutoff,
            ended_at__isnull=True,
        )
        .distinct()
        .order_by("created_at")
    )

    for session in stuck_accepted_sessions:
        expire_at = session.created_at + timedelta(seconds=CALL_MAX_DURATION_SECONDS)
        _finish_expired_session(session, CallSession.Status.ENDED, expire_at)
        expired_count += 1

    pending_cutoff = current_time - timedelta(seconds=CALL_PENDING_TIMEOUT_SECONDS)
    pending_sessions = (
        active_queryset.filter(
            status__in=[CallSession.Status.REQUESTED, CallSession.Status.RINGING],
            created_at__lte=pending_cutoff,
            ended_at__isnull=True,
        )
        .distinct()
        .order_by("created_at")
    )

    for session in pending_sessions:
        _finish_expired_session(session, CallSession.Status.MISSED, current_time)
        expired_count += 1

    return expired_count
