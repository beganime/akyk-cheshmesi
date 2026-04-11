import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AppRelease",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.CharField(db_index=True, max_length=40)),
                ("build_number", models.CharField(blank=True, max_length=32)),
                ("download_url", models.URLField(max_length=600)),
                ("changelog", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("released_at", models.DateTimeField(db_index=True)),
                ("min_android_version", models.CharField(blank=True, max_length=20)),
                ("available_platforms", models.JSONField(blank=True, default=list)),
            ],
            options={"db_table": "app_releases", "ordering": ["-released_at", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="apprelease",
            index=models.Index(fields=["version"], name="app_release_version_idx"),
        ),
        migrations.AddIndex(
            model_name="apprelease",
            index=models.Index(fields=["released_at"], name="app_release_released_idx"),
        ),
    ]
