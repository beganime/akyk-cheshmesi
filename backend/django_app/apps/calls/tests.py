import base64
import hashlib
import hmac
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.users.models import User


@override_settings(
    CALL_STUN_URLS=["stun:stun.example.test:3478"],
    CALL_TURN_URLS=["turn:turn.example.test:3478?transport=udp"],
    CALL_TURN_SECRET="test-turn-secret",
    CALL_TURN_TTL_SECONDS=600,
)
class CallIceConfigAPITests(TestCase):
    def setUp(self):
        with patch("apps.users.signals.sync_user_to_redis"):
            self.user = User.objects.create_user(
                email="turn-user@example.com",
                username="turn-user",
                password="StrongPass123",
                is_active=True,
            )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_returns_stun_and_short_lived_turn_credentials(self):
        response = self.client.get("/api/v1/calls/ice-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ice_servers"][0]["urls"], ["stun:stun.example.test:3478"])
        turn_config = response.data["ice_servers"][1]
        self.assertEqual(turn_config["urls"], ["turn:turn.example.test:3478?transport=udp"])
        expected_credential = base64.b64encode(
            hmac.new(
                b"test-turn-secret",
                turn_config["username"].encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("ascii")
        self.assertEqual(turn_config["credential"], expected_credential)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/v1/calls/ice-config/")

        self.assertEqual(response.status_code, 401)

    @override_settings(
        CALL_TURN_SECRET="",
        CALL_TURN_USERNAME="existing-user",
        CALL_TURN_CREDENTIAL="existing-password",
    )
    def test_supports_existing_long_term_turn_credentials(self):
        response = self.client.get("/api/v1/calls/ice-config/")

        self.assertEqual(response.status_code, 200)
        turn_config = response.data["ice_servers"][1]
        self.assertEqual(turn_config["username"], "existing-user")
        self.assertEqual(turn_config["credential"], "existing-password")
