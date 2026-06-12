from django.test import TestCase
from rest_framework.test import APIClient

from apps.bots.models import BotMembership, BotProfile
from apps.chats.models import Chat, ChatMember
from apps.messaging.models import Message
from apps.users.models import User


def create_active_user(email: str, username: str) -> User:
    return User.objects.create_user(
        email=email,
        username=username,
        password="StrongPass123",
        is_active=True,
        is_email_verified=True,
        registration_completed=True,
    )


class BotAPITests(TestCase):
    def setUp(self):
        self.owner = create_active_user("bot-owner@example.com", "botowner")
        self.member = create_active_user("bot-member@example.com", "botmember")
        self.client = APIClient()

    def test_create_bot_returns_token_once(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            "/api/bots/",
            {
                "username": "akyl_test_bot",
                "title": "Akyl Test Bot",
                "description": "Test bot",
                "scopes": ["send_message"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.data)
        bot = BotProfile.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bot.owner, self.owner)
        self.assertTrue(bot.token_hash)

    def test_add_bot_to_chat_and_send_message(self):
        chat = self._create_group()
        token, bot = self._create_bot()
        self.client.force_authenticate(self.owner)

        add_response = self.client.post(
            f"/api/chats/{chat.uuid}/bots/",
            {"bot_uuid": str(bot.uuid), "scopes": ["send_message"]},
            format="json",
        )
        self.assertEqual(add_response.status_code, 201)
        self.assertTrue(BotMembership.objects.filter(bot=bot, chat=chat, is_active=True).exists())
        self.assertTrue(ChatMember.objects.filter(chat=chat, user=bot.user, is_active=True).exists())

        send_response = self.client.post(
            "/api/bots/send-message/",
            {"chat_uuid": str(chat.uuid), "text": "Message from bot"},
            format="json",
            HTTP_AUTHORIZATION=f"Bot {token}",
        )

        self.assertEqual(send_response.status_code, 201)
        self.assertTrue(Message.objects.filter(chat=chat, sender=bot.user, text="Message from bot").exists())

    def test_regular_member_cannot_add_bot_to_group(self):
        chat = self._create_group()
        _, bot = self._create_bot()
        self.client.force_authenticate(self.member)

        response = self.client.post(
            f"/api/chats/{chat.uuid}/bots/",
            {"bot_uuid": str(bot.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def _create_bot(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/bots/",
            {"username": "helper_bot", "title": "Helper Bot", "scopes": ["send_message"]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data["token"], BotProfile.objects.get(uuid=response.data["uuid"])

    def _create_group(self) -> Chat:
        chat = Chat.objects.create(chat_type=Chat.ChatType.GROUP, title="Bot group", creator=self.owner, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.owner, role=ChatMember.Role.OWNER, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.member, role=ChatMember.Role.MEMBER, is_active=True)
        chat.members_count = 2
        chat.save(update_fields=["members_count", "updated_at"])
        return chat
