import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_phone_number"),
    ]

    operations = [
        migrations.CreateModel(
            name="DevicePushToken",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.CharField(db_index=True, max_length=512, unique=True)),
                ("provider", models.CharField(choices=[("fcm", "FCM"), ("apns", "APNs")], db_index=True, max_length=20)),
                ("platform", models.CharField(choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")], db_index=True, max_length=20)),
                ("device_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("device_name", models.CharField(blank=True, max_length=120)),
                ("app_version", models.CharField(blank=True, max_length=40)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_device_push_tokens",
                "ordering": ["-last_seen_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "is_active"], name="user_device_user_id_1ae60e_idx"),
                    models.Index(fields=["provider", "platform", "is_active"], name="user_device_provide_e2eb55_idx"),
                    models.Index(fields=["device_id"], name="user_device_device__005e8a_idx"),
                    models.Index(fields=["last_seen_at"], name="user_device_last_se_67cfdd_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "token"), name="uniq_device_push_user_token"),
                    models.UniqueConstraint(
                        condition=models.Q(is_active=True) & ~models.Q(device_id=""),
                        fields=("user", "provider", "platform", "device_id"),
                        name="uniq_device_push_user_device",
                    ),
                ],
            },
        ),
    ]
