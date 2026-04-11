import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BotProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(db_index=True, max_length=50, unique=True)),
                ("title", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"db_table": "bot_profiles", "ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="BotCommand",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("command", models.CharField(db_index=True, max_length=80)),
                ("response_text", models.TextField()),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="commands",
                        to="bots.botprofile",
                    ),
                ),
            ],
            options={"db_table": "bot_commands", "ordering": ["command"]},
        ),
        migrations.AddConstraint(
            model_name="botcommand",
            constraint=models.UniqueConstraint(fields=("bot", "command"), name="uniq_bot_command"),
        ),
    ]
