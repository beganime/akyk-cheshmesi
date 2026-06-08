from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.stories.models import Story


class Command(BaseCommand):
    help = "Deactivate stories whose expires_at is in the past."

    def handle(self, *args, **options):
        updated = Story.objects.filter(is_active=True, expires_at__lte=timezone.now()).update(
            is_active=False,
            updated_at=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS(f"Expired stories deactivated: {updated}"))
