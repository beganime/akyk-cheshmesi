from datetime import timedelta

from django.db import migrations
from django.db.models import Q
from django.utils import timezone


ACTIVE_STATUSES = ("requested", "ringing", "accepted")
MAX_DURATION_SECONDS = 60 * 60


def close_old_calls(apps, schema_editor):
    CallSession = apps.get_model("calls", "CallSession")
    CallParticipant = apps.get_model("calls", "CallParticipant")
    CallLog = apps.get_model("calls", "CallLog")

    now = timezone.now()
    cutoff = now - timedelta(seconds=MAX_DURATION_SECONDS)
    sessions = CallSession.objects.filter(status__in=ACTIVE_STATUSES).filter(
        Q(answered_at__isnull=False, answered_at__lte=cutoff)
        | Q(answered_at__isnull=True, created_at__lte=cutoff)
    )

    for session in sessions.iterator():
        previous_status = session.status
        target_status = "ended" if session.status == "accepted" else "missed"
        base_time = session.answered_at or session.created_at
        duration_seconds = max(int((now - base_time).total_seconds()), 0)

        CallSession.objects.filter(pk=session.pk).update(
            status=target_status,
            ended_at=now,
            duration_seconds=duration_seconds,
            updated_at=now,
        )

        for participant in CallParticipant.objects.filter(session_id=session.pk).iterator():
            if participant.status == "joined":
                participant_duration = 0
                if participant.joined_at:
                    participant_duration = max(int((now - participant.joined_at).total_seconds()), 0)
                CallParticipant.objects.filter(pk=participant.pk).update(
                    status="left",
                    left_at=now,
                    duration_seconds=participant_duration,
                    updated_at=now,
                )
            elif participant.status in {"invited", "ringing"}:
                CallParticipant.objects.filter(pk=participant.pk).update(
                    status="missed",
                    left_at=now,
                    updated_at=now,
                )

        CallLog.objects.create(
            session_id=session.pk,
            action="call_auto_cleanup",
            status_from=previous_status,
            status_to=target_status,
            duration_seconds=duration_seconds,
            payload={"max_duration_seconds": MAX_DURATION_SECONDS},
        )


class Migration(migrations.Migration):
    dependencies = [("calls", "0003_call_signals_logs_declined")]

    operations = [migrations.RunPython(close_old_calls, migrations.RunPython.noop)]
