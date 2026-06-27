from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone


ACTIVE_PENDING_STATUSES = {"requested", "ringing"}
ACCEPTED_STATUS = "accepted"
ENDED_STATUS = "ended"
MISSED_STATUS = "missed"
JOINED_STATUS = "joined"
LEFT_STATUS = "left"
PARTICIPANT_PENDING_STATUSES = {"invited", "ringing"}
PARTICIPANT_MISSED_STATUS = "missed"


def expire_existing_stale_calls(apps, schema_editor):
    CallSession = apps.get_model("calls", "CallSession")
    CallParticipant = apps.get_model("calls", "CallParticipant")
    CallLog = apps.get_model("calls", "CallLog")

    now = timezone.now()
    max_duration_seconds = int(getattr(settings, "CALL_MAX_DURATION_SECONDS", 60 * 60))
    pending_timeout_seconds = int(getattr(settings, "CALL_PENDING_TIMEOUT_SECONDS", 2 * 60))

    accepted_cutoff = now - timedelta(seconds=max_duration_seconds)
    pending_cutoff = now - timedelta(seconds=pending_timeout_seconds)

    expired_sessions = []

    accepted_sessions = CallSession.objects.filter(
        status=ACCEPTED_STATUS,
        answered_at__isnull=False,
        answered_at__lte=accepted_cutoff,
        ended_at__isnull=True,
    ).order_by("created_at")

    for session in accepted_sessions:
        expired_sessions.append((session, ENDED_STATUS, session.answered_at + timedelta(seconds=max_duration_seconds)))

    stuck_accepted_sessions = CallSession.objects.filter(
        status=ACCEPTED_STATUS,
        answered_at__isnull=True,
        created_at__lte=accepted_cutoff,
        ended_at__isnull=True,
    ).order_by("created_at")

    for session in stuck_accepted_sessions:
        expired_sessions.append((session, ENDED_STATUS, session.created_at + timedelta(seconds=max_duration_seconds)))

    pending_sessions = CallSession.objects.filter(
        status__in=ACTIVE_PENDING_STATUSES,
        created_at__lte=pending_cutoff,
        ended_at__isnull=True,
    ).order_by("created_at")

    for session in pending_sessions:
        expired_sessions.append((session, MISSED_STATUS, now))

    for session, next_status, ended_at in expired_sessions:
        previous_status = session.status
        base_time = session.answered_at or session.created_at
        duration_seconds = max(int((ended_at - base_time).total_seconds()), 0)

        session.status = next_status
        session.ended_at = ended_at
        session.duration_seconds = duration_seconds
        session.save(update_fields=["status", "ended_at", "duration_seconds", "updated_at"])

        for participant in CallParticipant.objects.filter(session=session, left_at__isnull=True):
            if participant.status == JOINED_STATUS:
                participant.status = LEFT_STATUS
                participant.left_at = ended_at
                if participant.joined_at:
                    participant.duration_seconds = max(int((ended_at - participant.joined_at).total_seconds()), 0)
                participant.save(update_fields=["status", "left_at", "duration_seconds", "updated_at"])
            elif participant.status in PARTICIPANT_PENDING_STATUSES:
                participant.status = PARTICIPANT_MISSED_STATUS
                participant.left_at = ended_at
                participant.save(update_fields=["status", "left_at", "updated_at"])

        CallLog.objects.create(
            session=session,
            action="call:auto-end:migration",
            status_from=previous_status,
            status_to=next_status,
            duration_seconds=duration_seconds,
            payload={
                "reason": "expired_migration",
                "max_duration_seconds": max_duration_seconds,
                "pending_timeout_seconds": pending_timeout_seconds,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("calls", "0003_call_signals_logs_declined"),
    ]

    operations = [
        migrations.RunPython(expire_existing_stale_calls, noop),
    ]
