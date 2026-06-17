from django.db import migrations, models


def expand_uploaded_media_file_path_columns(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE uploaded_media
            ALTER COLUMN file TYPE varchar(500),
            ALTER COLUMN thumbnail TYPE varchar(500);
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("mediafiles", "0004_ensure_uploaded_media_processing_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="uploadedmedia",
            name="file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="uploads/%Y/%m/%d/"),
        ),
        migrations.AlterField(
            model_name="uploadedmedia",
            name="thumbnail",
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to="uploads/thumbnails/%Y/%m/%d/",
            ),
        ),
        migrations.RunPython(expand_uploaded_media_file_path_columns, migrations.RunPython.noop),
    ]
