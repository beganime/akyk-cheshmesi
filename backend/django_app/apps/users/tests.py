from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import DevicePushToken, User


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
