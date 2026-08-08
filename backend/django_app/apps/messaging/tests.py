from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.chats.models import Chat, ChatMember
from apps.messaging.models import Message
from apps.messaging.tasks import enforce_support_chat_retention
from apps.users.tests import create_active_user


@override_settings(CHAT_RETENTION_ENABLED=True, CHAT_RETENTION_DAYS=90, CHAT_RETENTION_GRACE_DAYS=3)
class SupportChatRetentionTests(TestCase):
    def setUp(self):
        self.support = create_active_user('support@example.com', 'sl-support')
        self.support.is_staff = True
        self.support.save(update_fields=['is_staff', 'updated_at'])
        self.client_user = create_active_user('client@example.com', 'SL-2027-001')
        self.chat = Chat.objects.create(
            chat_type=Chat.ChatType.GROUP,
            title='Support',
            creator=self.support,
            direct_key='sl-support:sl-2027-001',
            is_active=True,
        )
        ChatMember.objects.create(chat=self.chat, user=self.support, role=ChatMember.Role.OWNER)
        ChatMember.objects.create(chat=self.chat, user=self.client_user, role=ChatMember.Role.MEMBER)
        old = timezone.now() - timedelta(days=91)
        message = Message.objects.create(chat=self.chat, sender=self.client_user, text='Старое сообщение')
        Message.objects.filter(pk=message.pk).update(created_at=old)
        Chat.objects.filter(pk=self.chat.pk).update(last_message_at=old)

    @patch('apps.messaging.tasks.send_new_message_push_notifications.delay')
    def test_warns_then_postpones_when_client_replies(self, push_mock):
        first = enforce_support_chat_retention.run()
        self.chat.refresh_from_db()

        self.assertEqual(first['warned'], 1)
        self.assertIsNotNone(self.chat.retention_delete_after)
        self.assertTrue(self.chat.messages.filter(metadata__retention_warning=True).exists())
        push_mock.assert_called_once()

        Message.objects.create(chat=self.chat, sender=self.client_user, text='Сохранить переписку')
        second = enforce_support_chat_retention.run()
        self.chat.refresh_from_db()

        self.assertEqual(second['postponed'], 1)
        self.assertIsNone(self.chat.retention_delete_after)

    @patch('apps.messaging.tasks.send_new_message_push_notifications.delay')
    def test_deletes_history_after_grace_period_without_reply(self, _push_mock):
        enforce_support_chat_retention.run()
        self.chat.refresh_from_db()
        self.chat.retention_delete_after = timezone.now() - timedelta(seconds=1)
        self.chat.save(update_fields=['retention_delete_after', 'updated_at'])

        result = enforce_support_chat_retention.run()
        self.chat.refresh_from_db()

        self.assertEqual(result['deleted'], 1)
        self.assertEqual(self.chat.messages.count(), 0)
        self.assertIsNone(self.chat.retention_warned_at)
