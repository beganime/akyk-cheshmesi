from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="message",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("system", "System"),
                    ("sticker", "Sticker"),
                    ("image", "Image"),
                    ("video", "Video"),
                    ("file", "File"),
                    ("audio", "Audio"),
                    ("video_note", "Video note"),
                ],
                db_index=True,
                default="text",
                max_length=16,
            ),
        ),
    ]
