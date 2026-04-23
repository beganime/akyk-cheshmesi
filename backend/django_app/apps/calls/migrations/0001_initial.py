import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chats", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallSession",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "call_type",
                    models.CharField(
                        choices=[("audio", "Audio"), ("video", "Video")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("ringing", "Ringing"),
                            ("accepted", "Accepted"),
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
                ("room_key", models.CharField(blank=True, db_index=True, default="", max_length=120, unique=True)),
                ("answered_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "chat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="calls",
                        to="chats.chat",
                    ),
                ),
                (
                    "initiated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="initiated_call_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "call_sessions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CallEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="call_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="calls.callsession",
                    ),
                ),
            ],
            options={
                "db_table": "call_events",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="CallParticipant",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("caller", "Caller"),
                            ("callee", "Callee"),
                            ("participant", "Participant"),
                        ],
                        db_index=True,
                        default="participant",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("invited", "Invited"),
                            ("ringing", "Ringing"),
                            ("joined", "Joined"),
                            ("declined", "Declined"),
                            ("missed", "Missed"),
                            ("left", "Left"),
                            ("failed", "Failed"),
                            ("busy", "Busy"),
                        ],
                        db_index=True,
                        default="invited",
                        max_length=16,
                    ),
                ),
                ("invited_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("joined_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("left_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("device_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("device_platform", models.CharField(blank=True, db_index=True, max_length=32)),
                ("device_name", models.CharField(blank=True, max_length=128)),
                ("is_muted", models.BooleanField(db_index=True, default=False)),
                ("is_video_enabled", models.BooleanField(db_index=True, default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants",
                        to="calls.callsession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="call_participants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "call_participants",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="callparticipant",
            constraint=models.UniqueConstraint(
                fields=("session", "user"),
                name="uniq_call_participant_session_user",
            ),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["uuid"], name="call_sessio_uuid_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["chat", "created_at"], name="call_sessio_chat_id_d91180_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["initiated_by", "created_at"], name="call_sessio_initiat_2f42d8_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["call_type", "status"], name="call_sessio_call_ty_9fd678_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["answered_at"], name="call_sessio_answere_813fd1_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["ended_at"], name="call_sessio_ended_a_bf8353_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["session", "status"], name="call_partic_session_eab0da_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["user", "status"], name="call_partic_user_id_5b6a32_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["role"], name="call_partic_role_7a56fd_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["joined_at"], name="call_partic_joined__eebcbb_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["left_at"], name="call_partic_left_at_93e535_idx"),
        ),
        migrations.AddIndex(
            model_name="callevent",
            index=models.Index(fields=["session", "created_at"], name="call_event_session_d6b7de_idx"),
        ),
        migrations.AddIndex(
            model_name="callevent",
            index=models.Index(fields=["event_type", "created_at"], name="call_event_event_t_5806f8_idx"),
        ),
    ]