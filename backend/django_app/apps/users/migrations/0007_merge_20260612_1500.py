from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_device_push_token"),
        ("users", "0006_devicepushtoken_and_more"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="devicepushtoken",
            new_name="user_device_user_id_51d489_idx",
            old_name="user_device_user_id_1ae60e_idx",
        ),
        migrations.RenameIndex(
            model_name="devicepushtoken",
            new_name="user_device_provide_1ad192_idx",
            old_name="user_device_provide_e2eb55_idx",
        ),
        migrations.RenameIndex(
            model_name="devicepushtoken",
            new_name="user_device_device__8253c9_idx",
            old_name="user_device_device__005e8a_idx",
        ),
        migrations.RenameIndex(
            model_name="devicepushtoken",
            new_name="user_device_last_se_e2d11e_idx",
            old_name="user_device_last_se_67cfdd_idx",
        ),
    ]
