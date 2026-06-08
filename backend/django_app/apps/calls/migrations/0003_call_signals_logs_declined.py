import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calls", "0002_fix_uuid_defaults"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="callsession",
            name="status",
            field=models.CharField(
                choices=[
                    ("requested", "Requested"),
                    ("ringing", "Ringing"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                    ("rejected", "Rejected"),
                    ("canceled", "Canceled"),
                    ("missed", "Missed"),
                    ("ended", "Ended"),
                    ("failed", "Failed"),
                    ("busy", "Busy"),
                ],
                db_index=True,
                default="requested",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="Call",
            fields=[],
            options={
                "verbose_name": "Call",
                "verbose_name_plural": "Calls",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("calls.callsession",),
        ),
        migrations.CreateModel(
            name="CallSignal",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("signal_type", models.CharField(choices=[("invite", "Invite"), ("accept", "Accept"), ("decline", "Decline"), ("end", "End"), ("missed", "Missed"), ("offer", "Offer"), ("answer", "Answer"), ("ice-candidate", "ICE candidate")], db_index=True, max_length=32)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_call_signals", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signals", to="calls.callsession")),
                ("target_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="received_call_signals", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "call_signals",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="CallLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action", models.CharField(db_index=True, max_length=64)),
                ("status_from", models.CharField(blank=True, db_index=True, max_length=32)),
                ("status_to", models.CharField(blank=True, db_index=True, max_length=32)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="call_logs", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="calls.callsession")),
            ],
            options={
                "db_table": "call_logs",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="callsignal",
            index=models.Index(fields=["session", "created_at"], name="call_signal_session_0f264b_idx"),
        ),
        migrations.AddIndex(
            model_name="callsignal",
            index=models.Index(fields=["sender", "created_at"], name="call_signal_sender__ba6e10_idx"),
        ),
        migrations.AddIndex(
            model_name="callsignal",
            index=models.Index(fields=["target_user", "created_at"], name="call_signal_target__1bfd2d_idx"),
        ),
        migrations.AddIndex(
            model_name="callsignal",
            index=models.Index(fields=["signal_type", "created_at"], name="call_signal_signal__bda25c_idx"),
        ),
        migrations.AddIndex(
            model_name="calllog",
            index=models.Index(fields=["session", "created_at"], name="call_logs_session_20bb26_idx"),
        ),
        migrations.AddIndex(
            model_name="calllog",
            index=models.Index(fields=["actor", "created_at"], name="call_logs_actor_i_f294a8_idx"),
        ),
        migrations.AddIndex(
            model_name="calllog",
            index=models.Index(fields=["action", "created_at"], name="call_logs_action__9a9b16_idx"),
        ),
        migrations.AddIndex(
            model_name="calllog",
            index=models.Index(fields=["status_to", "created_at"], name="call_logs_status__0658b8_idx"),
        ),
    ]
