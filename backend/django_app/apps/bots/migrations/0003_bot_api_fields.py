import apps.bots.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bots", "0002_seed_default_bot"),
        ("chats", "0002_chatmember_archived_at_chatmember_is_archived_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="botprofile",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="bot-avatars/"),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="last_used_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_bots",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="scopes",
            field=models.JSONField(blank=True, default=apps.bots.models.default_bot_scopes),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="token_hash",
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="token_last_rotated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bot_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="username",
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="botprofile",
            name="webhook_url",
            field=models.URLField(blank=True),
        ),
        migrations.CreateModel(
            name="BotMembership",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("scopes", models.JSONField(blank=True, default=apps.bots.models.default_bot_scopes)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "added_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="added_bot_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="bots.botprofile",
                    ),
                ),
                (
                    "chat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bot_memberships",
                        to="chats.chat",
                    ),
                ),
            ],
            options={
                "db_table": "bot_memberships",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="botprofile",
            index=models.Index(fields=["owner", "is_active"], name="bot_profile_owner_i_753ad0_idx"),
        ),
        migrations.AddIndex(
            model_name="botprofile",
            index=models.Index(fields=["username"], name="bot_profile_usernam_3aaa07_idx"),
        ),
        migrations.AddIndex(
            model_name="botprofile",
            index=models.Index(fields=["last_used_at"], name="bot_profile_last_us_af1067_idx"),
        ),
        migrations.AddConstraint(
            model_name="botmembership",
            constraint=models.UniqueConstraint(fields=("bot", "chat"), name="uniq_bot_chat_membership"),
        ),
        migrations.AddIndex(
            model_name="botmembership",
            index=models.Index(fields=["chat", "is_active"], name="bot_members_chat_id_2ca837_idx"),
        ),
        migrations.AddIndex(
            model_name="botmembership",
            index=models.Index(fields=["bot", "is_active"], name="bot_members_bot_id_89c5ef_idx"),
        ),
    ]
