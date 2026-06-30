from django.core.management.base import BaseCommand

from apps.calls.services import expire_stale_active_calls


class Command(BaseCommand):
    help = "Expire stale active call sessions and dispatch missed-call push notifications."

    def handle(self, *args, **options):
        expired_count = expire_stale_active_calls()
        self.stdout.write(self.style.SUCCESS(f"Expired stale calls: {expired_count}"))
