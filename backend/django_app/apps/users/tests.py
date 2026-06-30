from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.users.models import DevicePushToken, User
from apps.users.push_services import _fcm_payload, send_push_to_user_ids


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
