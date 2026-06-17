from django.db import migrations


def ensure_uploaded_media_processing_columns(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE uploaded_media
            ADD COLUMN IF NOT EXISTS thumbnail varchar(100) NULL,
            ADD COLUMN IF NOT EXISTS duration_seconds integer NULL,
            ADD COLUMN IF NOT EXISTS width integer NULL,
            ADD COLUMN IF NOT EXISTS height integer NULL,
            ADD COLUMN IF NOT EXISTS waveform_data jsonb NOT NULL DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS processed_at timestamp with time zone NULL,
            ADD COLUMN IF NOT EXISTS processing_error text NOT NULL DEFAULT '';
        """
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS uploaded_me_media__057bc7_idx "
        "ON uploaded_media (media_kind, duration_seconds);"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS uploaded_me_process_550fa4_idx "
        "ON uploaded_media (processed_at);"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("mediafiles", "0003_media_processing_fields"),
    ]

    operations = [
        migrations.RunPython(ensure_uploaded_media_processing_columns, migrations.RunPython.noop),
    ]
