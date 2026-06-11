from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chats.models import Chat, ChatMember
from apps.chats.utils import build_direct_chat_key
from apps.messaging.models import Message
from apps.stories.models import Story, StoryView
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


def create_direct_chat(user_a: User, user_b: User) -> Chat:
    chat = Chat.objects.create(
        chat_type=Chat.ChatType.DIRECT,
        direct_key=build_direct_chat_key(user_a.uuid, user_b.uuid),
        creator=user_a,
        members_count=2,
        is_active=True,
    )
    ChatMember.objects.create(chat=chat, user=user_a, role=ChatMember.Role.OWNER, is_active=True)
    ChatMember.objects.create(chat=chat, user=user_b, role=ChatMember.Role.MEMBER, is_active=True)
    return chat


@override_settings(FCM_ENABLED=False)
class StoryInteractionAPITests(TestCase):
    def setUp(self):
        self.author = create_active_user("author@example.com", "author")
        self.viewer = create_active_user("viewer@example.com", "viewer")
        create_direct_chat(self.author, self.viewer)
        self.story = Story.objects.create(
            author=self.author,
            media_type=Story.MediaType.TEXT,
            caption="Today",
            expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.viewer)

    @patch("apps.stories.views.publish_realtime_event")
    def test_story_reply_creates_direct_message(self, publish_mock):
        response = self.client.post(
            f"/api/stories/{self.story.uuid}/reply/",
            {"text": "Nice story"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        message = Message.objects.get(uuid=response.data["message"]["uuid"])
        self.assertEqual(message.sender, self.viewer)
        self.assertEqual(message.chat.chat_type, Chat.ChatType.DIRECT)
        self.assertEqual(message.metadata["story_uuid"], str(self.story.uuid))
        self.assertEqual(message.metadata["story_action"], "reply")
        self.assertTrue(StoryView.objects.filter(story=self.story, viewer=self.viewer).exists())
        self.assertTrue(publish_mock.called)

    @patch("apps.stories.views.publish_realtime_event")
    def test_story_reaction_creates_direct_message(self, publish_mock):
        response = self.client.post(
            f"/api/stories/{self.story.uuid}/react/",
            {"emoji": "🔥"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        message = Message.objects.get(uuid=response.data["message"]["uuid"])
        self.assertEqual(message.text, "🔥")
        self.assertEqual(message.metadata["story_action"], "reaction")
        self.assertEqual(message.metadata["reaction"], "🔥")
        self.assertTrue(publish_mock.called)
