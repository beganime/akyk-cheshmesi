import apps.stories.models
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mediafiles", "0002_uploadedmedia_media_kind_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Story",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Video"), ("text", "Text")], db_index=True, max_length=16)),
                ("caption", models.TextField(blank=True)),
                ("background", models.CharField(blank=True, max_length=64)),
                ("expires_at", models.DateTimeField(db_index=True, default=apps.stories.models.default_story_expires_at)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stories", to=settings.AUTH_USER_MODEL)),
                ("media", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stories", to="mediafiles.uploadedmedia")),
            ],
            options={
                "db_table": "stories",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StoryView",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("viewed_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="stories.story")),
                ("viewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="story_views", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "story_views",
                "ordering": ["-viewed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="story",
            index=models.Index(fields=["author", "-created_at"], name="stories_author__9fb739_idx"),
        ),
        migrations.AddIndex(
            model_name="story",
            index=models.Index(fields=["is_active", "expires_at"], name="stories_is_acti_5d7550_idx"),
        ),
        migrations.AddIndex(
            model_name="story",
            index=models.Index(fields=["media_type", "created_at"], name="stories_media_t_c4ab4e_idx"),
        ),
        migrations.AddIndex(
            model_name="storyview",
            index=models.Index(fields=["story", "viewed_at"], name="story_views_story_i_87f944_idx"),
        ),
        migrations.AddIndex(
            model_name="storyview",
            index=models.Index(fields=["viewer", "viewed_at"], name="story_views_viewer__92a91b_idx"),
        ),
        migrations.AddConstraint(
            model_name="storyview",
            constraint=models.UniqueConstraint(fields=("story", "viewer"), name="uniq_story_viewer"),
        ),
    ]
