from django.test import TestCase
from rest_framework.test import APIClient

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


class ChatPermissionAPITests(TestCase):
    def setUp(self):
        self.owner = create_active_user("owner@example.com", "owner")
        self.member = create_active_user("member@example.com", "member")
        self.admin = create_active_user("admin@example.com", "admin")
        self.outsider = create_active_user("outsider@example.com", "outsider")
        self.client = APIClient()

    def test_create_private_chat(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            "/api/chats/",
            {"type": "private", "peer_uuid": str(self.member.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Chat.objects.filter(chat_type=Chat.ChatType.DIRECT).count(), 1)
        chat = Chat.objects.get(chat_type=Chat.ChatType.DIRECT)
        self.assertEqual(chat.members.filter(is_active=True).count(), 2)

    def test_group_owner_adds_and_removes_member(self):
        chat = self._create_group()
        new_member = create_active_user("new@example.com", "newbie")
        self.client.force_authenticate(self.owner)

        add_response = self.client.post(
            f"/api/chats/{chat.uuid}/members/",
            {"user_uuid": str(new_member.uuid)},
            format="json",
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(ChatMember.objects.filter(chat=chat, user=new_member, is_active=True).exists())

        remove_response = self.client.delete(f"/api/chats/{chat.uuid}/members/{new_member.uuid}/")
        self.assertEqual(remove_response.status_code, 204)
        self.assertFalse(ChatMember.objects.get(chat=chat, user=new_member).is_active)

    def test_removed_member_cannot_read_chat(self):
        chat = self._create_group()
        ChatMember.objects.filter(chat=chat, user=self.member).update(is_active=False)
        self.client.force_authenticate(self.member)

        response = self.client.get(f"/api/chats/{chat.uuid}/messages/")

        self.assertEqual(response.status_code, 404)

    def test_send_message_as_group_member(self):
        chat = self._create_group()
        self.client.force_authenticate(self.member)

        response = self.client.post(
            f"/api/chats/{chat.uuid}/messages/",
            {"message_type": "text", "text": "Hello group"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Message.objects.filter(chat=chat, sender=self.member, text="Hello group").exists())

    def test_owner_can_promote_and_demote_admin(self):
        chat = self._create_group()
        self.client.force_authenticate(self.owner)

        promote_response = self.client.post(
            f"/api/chats/{chat.uuid}/admins/",
            {"user_uuid": str(self.member.uuid)},
            format="json",
        )
        self.assertEqual(promote_response.status_code, 200)
        self.assertEqual(ChatMember.objects.get(chat=chat, user=self.member).role, ChatMember.Role.ADMIN)

        demote_response = self.client.delete(f"/api/chats/{chat.uuid}/admins/{self.member.uuid}/")
        self.assertEqual(demote_response.status_code, 200)
        self.assertEqual(ChatMember.objects.get(chat=chat, user=self.member).role, ChatMember.Role.MEMBER)

    def test_regular_member_cannot_remove_group_member(self):
        chat = self._create_group()
        self.client.force_authenticate(self.member)

        response = self.client.delete(f"/api/chats/{chat.uuid}/members/{self.admin.uuid}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ChatMember.objects.get(chat=chat, user=self.admin).is_active)

    def _create_group(self) -> Chat:
        chat = Chat.objects.create(
            chat_type=Chat.ChatType.GROUP,
            title="Study group",
            creator=self.owner,
            is_active=True,
        )
        ChatMember.objects.create(chat=chat, user=self.owner, role=ChatMember.Role.OWNER, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.member, role=ChatMember.Role.MEMBER, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.admin, role=ChatMember.Role.ADMIN, is_active=True)
        chat.members_count = 3
        chat.save(update_fields=["members_count", "updated_at"])
        return chat
