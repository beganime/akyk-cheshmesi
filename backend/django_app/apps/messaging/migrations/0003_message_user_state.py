import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0002_add_video_note_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageUserState",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_hidden", models.BooleanField(db_index=True, default=False)),
                ("hidden_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_states",
                        to="messaging.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "message_user_states",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="messageuserstate",
            constraint=models.UniqueConstraint(fields=("message", "user"), name="uniq_message_user_state"),
        ),
        migrations.AddIndex(
            model_name="messageuserstate",
            index=models.Index(fields=["user", "is_hidden"], name="message_use_user_id_d64f75_idx"),
        ),
        migrations.AddIndex(
            model_name="messageuserstate",
            index=models.Index(fields=["message", "user"], name="message_use_message_984f42_idx"),
        ),
        migrations.AddIndex(
            model_name="messageuserstate",
            index=models.Index(fields=["hidden_at"], name="message_use_hidden__e56555_idx"),
        ),
    ]
