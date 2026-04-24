import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="callsession",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True),
        ),
        migrations.AlterField(
            model_name="callparticipant",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True),
        ),
        migrations.AlterField(
            model_name="callevent",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True),
        ),
    ]