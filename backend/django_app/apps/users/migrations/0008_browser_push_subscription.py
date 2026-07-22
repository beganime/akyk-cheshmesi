import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_merge_20260612_1500"),
    ]

    operations = [
        migrations.CreateModel(
            name="BrowserPushSubscription",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("endpoint", models.URLField(max_length=2000, unique=True)),
                ("p256dh", models.CharField(max_length=255)),
                ("auth", models.CharField(max_length=255)),
                ("device_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="browser_push_subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "user_browser_push_subscriptions",
                "ordering": ["-last_seen_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "is_active"], name="user_browse_user_id_1eff89_idx"),
                    models.Index(fields=["device_id"], name="user_browse_device__09258e_idx"),
                    models.Index(fields=["last_seen_at"], name="user_browse_last_se_0355ec_idx"),
                ],
            },
        ),
    ]
