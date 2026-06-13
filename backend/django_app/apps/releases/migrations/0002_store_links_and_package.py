from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("releases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="apprelease",
            name="platform",
            field=models.CharField(choices=[("android", "Android"), ("ios", "iOS"), ("windows", "Windows"), ("macos", "macOS"), ("web", "Web")], db_index=True, default="android", max_length=24),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="channel",
            field=models.CharField(choices=[("internal", "Internal"), ("testing", "Testing"), ("beta", "Beta"), ("production", "Production")], db_index=True, default="testing", max_length=24),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="store_status",
            field=models.CharField(choices=[("draft", "Draft"), ("testing", "Testing"), ("review", "On review"), ("live", "Live")], db_index=True, default="draft", max_length=24),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="package_file",
            field=models.FileField(blank=True, null=True, upload_to="app_packages/android/"),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="google_play_url",
            field=models.URLField(blank=True, max_length=600),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="testflight_url",
            field=models.URLField(blank=True, max_length=600),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="file_size_bytes",
            field=models.PositiveBigIntegerField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name="apprelease",
            name="is_public",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AlterField(
            model_name="apprelease",
            name="download_url",
            field=models.URLField(blank=True, max_length=600),
        ),
        migrations.AddIndex(
            model_name="apprelease",
            index=models.Index(fields=["platform", "is_active"], name="app_release_platform_7d6ca0_idx"),
        ),
        migrations.AddIndex(
            model_name="apprelease",
            index=models.Index(fields=["channel", "store_status"], name="app_release_channel_32ce62_idx"),
        ),
    ]
