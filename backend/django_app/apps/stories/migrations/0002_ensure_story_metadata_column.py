from django.db import migrations


def ensure_story_metadata_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        "ALTER TABLE stories "
        "ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("stories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(ensure_story_metadata_column, migrations.RunPython.noop),
    ]
