from django.conf import settings
from django.core.management.base import BaseCommand

from apps.messaging.stream_bridge import MessageStreamSaver


class Command(BaseCommand):
    help = "Consume Redis stream messages and persist them to PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--consumer",
            type=str,
            default="",
            help="Consumer name. If omitted, an auto-generated one will be used.",
        )
        parser.add_argument(
            "--group",
            type=str,
            default=getattr(settings, "REDIS_STREAM_MESSAGES_GROUP", "message-savers"),
            help="Redis consumer group name",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=getattr(settings, "REDIS_STREAM_READ_COUNT", 20),
            help="How many entries to fetch per batch",
        )
        parser.add_argument(
            "--block-ms",
            type=int,
            default=getattr(settings, "REDIS_STREAM_BLOCK_MS", 5000),
            help="Blocking timeout for XREADGROUP in milliseconds",
        )
        parser.add_argument(
            "--claim-idle-ms",
            type=int,
            default=getattr(settings, "REDIS_STREAM_CLAIM_IDLE_MS", 60000),
            help="Idle time after which pending entries are reclaimed",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Read one batch and exit",
        )

    def handle(self, *args, **options):
        consumer_name = options["consumer"] or MessageStreamSaver.build_default_consumer_name()

        saver = MessageStreamSaver(
            stream_key=getattr(settings, "REDIS_STREAM_MESSAGES_KEY", "stream:messages"),
            group_name=options["group"],
            consumer_name=consumer_name,
            dlq_key=getattr(settings, "REDIS_STREAM_DLQ_KEY", "stream:messages:dlq"),
        )

        self.stdout.write(
            self.style.NOTICE(
                f"Starting stream saver | stream={saver.stream_key} group={saver.group_name} consumer={saver.consumer_name}"
            )
        )

        if options["once"]:
            processed = saver.consume_once(
                count=options["count"],
                claim_idle_ms=options["claim_idle_ms"],
            )
            self.stdout.write(self.style.SUCCESS(f"Done. Processed entries: {processed}"))
            return

        saver.consume_forever(
            block_ms=options["block_ms"],
            count=options["count"],
            claim_idle_ms=options["claim_idle_ms"],
        )