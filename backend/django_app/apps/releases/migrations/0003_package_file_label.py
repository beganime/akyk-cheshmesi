from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("releases", "0002_store_links_and_package")]

    operations = [
        migrations.AlterField(
            model_name="apprelease",
            name="package_file",
            field=models.FileField("Файл сборки", blank=True, null=True, upload_to="app_packages/android/"),
        ),
    ]
