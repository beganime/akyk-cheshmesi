from django.core.management.base import BaseCommand

from apps.chats.models import Chat, ChatMember
from apps.chats.redis_sync import sync_chat_member_to_redis, sync_chat_to_redis
from apps.messaging.models import Message
from apps.messaging.redis_sync import append_message_to_history_cache, clear_chat_history_cache
from apps.users.models import User
from apps.users.redis_sync import sync_user_to_redis


class Command(BaseCommand):
    help = "Warm Redis cache from PostgreSQL data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Warming users cache..."))
        users_count = 0
        for user in User.objects.iterator():
            sync_user_to_redis(user)
            users_count += 1

        self.stdout.write(self.style.NOTICE("Warming chats cache..."))
        chats_count = 0
        for chat in Chat.objects.select_related("creator").iterator():
            sync_chat_to_redis(chat)
            chats_count += 1

        self.stdout.write(self.style.NOTICE("Warming chat members cache..."))
        members_count = 0
        for member in ChatMember.objects.select_related("chat", "user").iterator():
            sync_chat_member_to_redis(member)
            members_count += 1

        self.stdout.write(self.style.NOTICE("Warming history cache..."))
        history_chats_count = 0
        for chat in Chat.objects.iterator():
            clear_chat_history_cache(chat.uuid)

            messages = (
                Message.objects.filter(chat=chat)
                .select_related("chat", "sender", "reply_to")
                .order_by("-created_at")[:50]
            )

            for message in reversed(list(messages)):
                append_message_to_history_cache(message)

            history_chats_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Redis warmup complete | users={users_count}, chats={chats_count}, "
                f"members={members_count}, history_chats={history_chats_count}"
            )
        )