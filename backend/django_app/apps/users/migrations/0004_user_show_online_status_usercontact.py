import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_onetimecode_id_alter_user_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="show_online_status",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.CreateModel(
            name="UserContact",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source", models.CharField(db_index=True, default="chat", max_length=32)),
                ("last_interaction_at", models.DateTimeField(db_index=True)),
                ("is_favorite", models.BooleanField(db_index=True, default=False)),
                (
                    "contact_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="in_contacts_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contacts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_contacts",
                "ordering": ["-last_interaction_at", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="usercontact",
            constraint=models.UniqueConstraint(fields=("owner", "contact_user"), name="uniq_user_contact"),
        ),
        migrations.AddIndex(
            model_name="usercontact",
            index=models.Index(fields=["owner", "last_interaction_at"], name="user_contact_owner_interaction_idx"),
        ),
        migrations.AddIndex(
            model_name="usercontact",
            index=models.Index(fields=["owner", "is_favorite"], name="user_contact_owner_favorite_idx"),
        ),
    ]
