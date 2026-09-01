from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.users.models import BrowserPushSubscription, DevicePushToken, User
from apps.users.push_services import _fcm_payload, dispatch_call_push, send_message_push_by_id, send_push_to_user_ids
from apps.chats.models import Chat, ChatMember
from apps.calls.models import CallParticipant, CallSession
from apps.messaging.models import Message


def create_active_user(email: str, username: str) -> User:
    return User.objects.create_user(
        email=email,
        username=username,
        password="StrongPass123",
        is_active=True,
        is_email_verified=True,
        registration_completed=True,
    )


class PushTokenAPITests(TestCase):
    def setUp(self):
        self.user = create_active_user("user@example.com", "user")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_register_push_token(self):
        response = self.client.post(
            "/api/push-tokens/",
            {
                "token": "fcm-token-1",
                "provider": "fcm",
                "platform": "android",
                "device_id": "android-1",
                "device_name": "Pixel",
                "app_version": "1.0.0",
                "meta": {"locale": "ru"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DevicePushToken.objects.count(), 1)
        push_token = DevicePushToken.objects.get()
        self.assertTrue(push_token.is_active)
        self.assertEqual(push_token.device_id, "android-1")

    def test_device_token_alias_replaces_same_device(self):
        DevicePushToken.objects.create(
            user=self.user,
            token="old-token",
            provider=DevicePushToken.Provider.FCM,
            platform=DevicePushToken.Platform.ANDROID,
            device_id="android-1",
        )

        response = self.client.post(
            "/api/device-tokens/",
            {
                "token": "new-token",
                "provider": "fcm",
                "platform": "android",
                "device_id": "android-1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(DevicePushToken.objects.get(token="new-token").is_active)
        self.assertFalse(DevicePushToken.objects.get(token="old-token").is_active)

    def test_register_push_tokens_keeps_different_devices_active(self):
        self.client.post(
            "/api/push-tokens/",
            {
                "token": "phone-token",
                "provider": "fcm",
                "platform": "android",
                "device_id": "android-phone",
            },
            format="json",
        )
        self.client.post(
            "/api/push-tokens/",
            {
                "token": "tablet-token",
                "provider": "fcm",
                "platform": "android",
                "device_id": "android-tablet",
            },
            format="json",
        )

        self.assertEqual(DevicePushToken.objects.filter(user=self.user, is_active=True).count(), 2)

    def test_delete_push_token_deactivates(self):
        DevicePushToken.objects.create(
            user=self.user,
            token="token-to-delete",
            provider=DevicePushToken.Provider.FCM,
            platform=DevicePushToken.Platform.ANDROID,
            device_id="android-1",
        )

        response = self.client.delete(
            "/api/push-tokens/",
            {"token": "token-to-delete"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DevicePushToken.objects.get(token="token-to-delete").is_active)

    @override_settings(
        WEB_PUSH_ENABLED=True,
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
    )
    def test_register_browser_push_subscription(self):
        response = self.client.post(
            "/api/web-push/subscriptions/",
            {
                "endpoint": "https://push.example.test/subscription-1",
                "keys": {"p256dh": "browser-public-key", "auth": "browser-auth-key"},
                "device_id": "web-browser-1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        subscription = BrowserPushSubscription.objects.get()
        self.assertEqual(subscription.user, self.user)
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.device_id, "web-browser-1")

    @override_settings(
        WEB_PUSH_ENABLED=True,
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
    )
    def test_browser_push_config_returns_public_key(self):
        response = self.client.get("/api/web-push/config/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["enabled"])
        self.assertEqual(response.data["public_key"], "public-key")

    def test_fcm_payload_uses_message_channel_by_default(self):
        push_token = DevicePushToken(token="fcm-token-1")

        payload = _fcm_payload(
            push_token,
            "New message",
            "Hello",
            {"type": "message", "chat_uuid": "chat-1"},
        )

        message = payload["message"]
        self.assertEqual(message["android"]["notification"]["channel_id"], "messages")
        self.assertNotIn("ttl", message["android"])
        self.assertEqual(message["data"]["channel_id"], "messages")
        self.assertEqual(message["data"]["chat_uuid"], "chat-1")
        self.assertEqual(message["apns"]["headers"]["apns-push-type"], "alert")

    def test_fcm_payload_uses_calls_channel_for_incoming_call(self):
        push_token = DevicePushToken(token="fcm-token-1")

        payload = _fcm_payload(
            push_token,
            "Incoming call",
            "User is calling",
            {"type": "call", "call_uuid": "call-1"},
        )

        message = payload["message"]
        self.assertEqual(message["android"]["notification"]["channel_id"], "calls")
        self.assertEqual(message["android"]["ttl"], "60s")
        self.assertEqual(message["data"]["channel_id"], "calls")
        self.assertEqual(message["data"]["call_uuid"], "call-1")
        self.assertEqual(message["apns"]["payload"]["aps"]["content-available"], 1)
        self.assertEqual(message["apns"]["payload"]["aps"]["interruption-level"], "time-sensitive")

    @override_settings(FCM_ENABLED=True)
    def test_send_push_to_user_ids_sends_active_fcm_tokens(self):
        DevicePushToken.objects.create(
            user=self.user,
            token="fcm-token-1",
            provider=DevicePushToken.Provider.FCM,
            platform=DevicePushToken.Platform.ANDROID,
            device_id="android-1",
        )

        with patch("apps.users.push_services._send_fcm_message", return_value=True) as send_mock:
            result = send_push_to_user_ids(
                [self.user.id],
                "New message",
                "Hello",
                {"type": "message"},
            )

        self.assertEqual(result.attempted_count, 1)
        self.assertEqual(result.sent_count, 1)
        send_mock.assert_called_once()

    @override_settings(
        WEB_PUSH_ENABLED=True,
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
    )
    def test_send_push_to_user_ids_sends_browser_subscription(self):
        subscription = BrowserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.test/subscription-1",
            p256dh="browser-public-key",
            auth="browser-auth-key",
            device_id="web-browser-1",
        )

        with patch("apps.users.push_services._send_browser_push", return_value=True) as send_mock:
            result = send_push_to_user_ids(
                [self.user.id],
                "New message",
                "Hello",
                {"type": "message", "chat_uuid": "chat-1"},
            )

        self.assertEqual(result.attempted_count, 1)
        self.assertEqual(result.sent_count, 1)
        send_mock.assert_called_once_with(subscription, "New message", "Hello", {"type": "message", "chat_uuid": "chat-1"})


class PushDeliveryTests(TestCase):
    def setUp(self):
        self.sender = create_active_user("sender@example.com", "sender")
        self.recipient = create_active_user("recipient@example.com", "recipient")
        self.chat = Chat.objects.create(chat_type=Chat.ChatType.DIRECT, creator=self.sender, members_count=2)
        ChatMember.objects.create(chat=self.chat, user=self.sender, role=ChatMember.Role.OWNER)
        ChatMember.objects.create(chat=self.chat, user=self.recipient, role=ChatMember.Role.MEMBER)

    @override_settings(FCM_ENABLED=True)
    def test_message_push_targets_chat_recipient_with_required_data(self):
        message = Message.objects.create(chat=self.chat, sender=self.sender, text="Hello from mobile")

        with patch("apps.users.push_services.send_push_to_user_ids") as push_mock:
            send_message_push_by_id(message.id)

        push_mock.assert_called_once()
        user_ids, title, body, data = push_mock.call_args.args
        self.assertEqual(user_ids, [self.recipient.id])
        self.assertEqual(data["type"], "message")
        self.assertEqual(data["channel_id"], "messages")
        self.assertEqual(data["chat_uuid"], str(self.chat.uuid))
        self.assertEqual(data["message_uuid"], str(message.uuid))
        self.assertEqual(data["sender_name"], "sender")
        self.assertEqual(data["preview"], "Hello from mobile")

    @override_settings(FCM_ENABLED=True)
    def test_call_push_targets_callee_with_required_data(self):
        session = CallSession.objects.create(
            chat=self.chat,
            initiated_by=self.sender,
            call_type=CallSession.CallType.VIDEO,
            status=CallSession.Status.RINGING,
        )
        CallParticipant.objects.create(
            session=session,
            user=self.sender,
            role=CallParticipant.Role.CALLER,
            status=CallParticipant.Status.JOINED,
        )
        CallParticipant.objects.create(
            session=session,
            user=self.recipient,
            role=CallParticipant.Role.CALLEE,
            status=CallParticipant.Status.RINGING,
        )

        with patch("apps.users.push_services.dispatch_push_to_user_ids") as push_mock:
            dispatch_call_push(session.id, "call")

        push_mock.assert_called_once()
        user_ids, title, body, data = push_mock.call_args.args
        self.assertEqual(user_ids, [self.recipient.id])
        self.assertEqual(data["type"], "call")
        self.assertEqual(data["event"], "incoming_call")
        self.assertEqual(data["channel_id"], "calls")
        self.assertEqual(data["call_uuid"], str(session.uuid))
        self.assertEqual(data["chat_uuid"], str(self.chat.uuid))
        self.assertEqual(data["room_key"], session.room_key)
        self.assertEqual(data["call_type"], "video")
        self.assertEqual(data["caller_uuid"], str(self.sender.uuid))

    @override_settings(FCM_ENABLED=True)
    def test_missed_call_push_does_not_target_caller(self):
        session = CallSession.objects.create(
            chat=self.chat,
            initiated_by=self.sender,
            call_type=CallSession.CallType.AUDIO,
            status=CallSession.Status.MISSED,
        )

        with patch("apps.users.push_services.dispatch_push_to_user_ids") as push_mock:
            dispatch_call_push(session.id, "missed_call")

        push_mock.assert_called_once()
        user_ids, title, body, data = push_mock.call_args.args
        self.assertEqual(user_ids, [self.recipient.id])
        self.assertEqual(data["type"], "missed_call")
        self.assertEqual(data["event"], "missed_call")
        self.assertEqual(data["channel_id"], "calls")


class UserProfileAPITests(TestCase):
    def setUp(self):
        self.user = create_active_user("profile@example.com", "profile")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_patch_me_is_partial(self):
        response = self.client.patch(
            "/api/users/me/",
            {"first_name": "Akyl"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Akyl")
        self.assertEqual(response.data["username"], "profile")


class AuthLoginAPITests(TestCase):
    def setUp(self):
        self.user = create_active_user("login@example.com", "mobilelogin")
        self.client = APIClient()

    def test_login_accepts_username_identifier(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "identifier": "mobilelogin",
                "password": "StrongPass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data["tokens"])


@override_settings(MANAGER_SL_SERVICE_TOKEN="sl-service-test-token")
class SLInternalSupportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth = {"HTTP_AUTHORIZATION": "Bearer sl-service-test-token"}

    def provision(self):
        return self.client.post(
            "/api/v1/internal/sl/provision/",
            {
                "sl_id": "SL-001",
                "full_name": "Тестовый Клиент",
                "password": "Test_0710",
            },
            format="json",
            **self.auth,
        )

    def test_provision_is_idempotent_and_creates_support_chat(self):
        first = self.provision()
        second = self.provision()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(User.objects.filter(username="SL-001").count(), 1)
        self.assertEqual(Chat.objects.filter(direct_key="sl-support:sl-001").count(), 1)
        chat = Chat.objects.get(direct_key="sl-support:sl-001")
        self.assertEqual(chat.members.filter(is_active=True).count(), 2)
        self.assertEqual(first.data["chat_uuid"], second.data["chat_uuid"])

    def test_support_chat_accepts_client_and_manager_messages(self):
        self.provision()
        client_message = self.client.post(
            "/api/v1/internal/sl/support-chats/SL-001/messages/",
            {"actor": "client", "text": "Здравствуйте"},
            format="json",
            **self.auth,
        )
        manager_message = self.client.post(
            "/api/v1/internal/sl/support-chats/SL-001/messages/",
            {"actor": "manager", "manager_name": "Наргиза", "text": "Добрый день"},
            format="json",
            **self.auth,
        )
        history = self.client.get(
            "/api/v1/internal/sl/support-chats/SL-001/messages/?actor=client",
            **self.auth,
        )

        self.assertEqual(client_message.status_code, 201)
        self.assertEqual(manager_message.status_code, 201)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["count"], 2)
        self.assertTrue(history.data["results"][0]["is_mine"])
        self.assertEqual(history.data["results"][1]["sender_role"], "manager")
        self.assertEqual(history.data["results"][1]["sender_display_name"], "Наргиза")

    def test_internal_endpoints_require_service_token(self):
        response = self.client.post(
            "/api/v1/internal/sl/provision/",
            {"sl_id": "SL-001", "full_name": "Тест", "password": "Test_0710"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
