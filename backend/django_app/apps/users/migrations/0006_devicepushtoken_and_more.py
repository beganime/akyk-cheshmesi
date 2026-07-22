import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_user_phone_number"),
    ]

    # This branch existed on production before 0006_device_push_token was
    # committed. Keep only its non-duplicate schema operations so new
    # databases can apply both historical branches safely.
    operations = [
        migrations.RenameIndex(
            model_name="usercontact",
            new_name="user_contac_owner_i_49d7dc_idx",
            old_name="user_contact_owner_interaction_idx",
        ),
        migrations.RenameIndex(
            model_name="usercontact",
            new_name="user_contac_owner_i_ee29e1_idx",
            old_name="user_contact_owner_favorite_idx",
        ),
        migrations.AlterField(
            model_name="usercontact",
            name="last_interaction_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="usercontact",
            name="uuid",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["phone_number"], name="users_phone_n_a3b1c5_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["show_online_status"], name="users_show_on_80e267_idx"),
        ),
    ]
