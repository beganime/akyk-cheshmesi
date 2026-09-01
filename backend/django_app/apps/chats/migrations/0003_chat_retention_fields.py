from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('chats', '0002_chatmember_archived_at_chatmember_is_archived_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='retention_warned_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='chat',
            name='retention_delete_after',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
