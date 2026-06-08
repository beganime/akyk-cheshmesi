from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mediafiles", "0002_uploadedmedia_media_kind_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadedmedia",
            name="thumbnail",
            field=models.ImageField(blank=True, null=True, upload_to="uploads/thumbnails/%Y/%m/%d/"),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="duration_seconds",
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="width",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="height",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="waveform_data",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="processed_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="uploadedmedia",
            name="processing_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="uploadedmedia",
            index=models.Index(fields=["media_kind", "duration_seconds"], name="uploaded_me_media__057bc7_idx"),
        ),
        migrations.AddIndex(
            model_name="uploadedmedia",
            index=models.Index(fields=["processed_at"], name="uploaded_me_process_550fa4_idx"),
        ),
    ]
