import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.chats.models import Chat, ChatMember
from apps.mediafiles.models import MessageAttachment, UploadedMedia
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


@override_settings(
    USE_S3=False,
    MEDIA_USE_X_ACCEL_REDIRECT=False,
    MEDIA_ALLOWED_CONTENT_TYPES=["text/plain", "image/jpeg"],
    MEDIA_ALLOWED_EXTENSIONS=["txt", "jpg", "jpeg"],
    MEDIA_BLOCKED_EXTENSIONS=["php", "js", "svg"],
)
class LocalMediaAPITests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.owner = create_active_user("media-owner@example.com", "mediaowner")
        self.member = create_active_user("media-member@example.com", "mediamember")
        self.outsider = create_active_user("media-outsider@example.com", "mediaoutsider")
        self.client = APIClient()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_upload_local_media(self):
        self.client.force_authenticate(self.owner)
        file_obj = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")

        response = self.client.post("/api/media/upload-local/", {"file": file_obj}, format="multipart")

        self.assertEqual(response.status_code, 201)
        media = UploadedMedia.objects.get(uuid=response.data["uuid"])
        self.assertEqual(media.storage_provider, UploadedMedia.StorageProvider.LOCAL)
        self.assertEqual(media.media_kind, UploadedMedia.MediaKind.FILE)
        self.assertIn("/api/media/", response.data["file_url"])

    def test_reject_dangerous_extension(self):
        self.client.force_authenticate(self.owner)
        file_obj = SimpleUploadedFile("payload.php", b"<?php echo 1;", content_type="text/plain")

        response = self.client.post("/api/media/upload-local/", {"file": file_obj}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("extension", response.data["detail"])

    def test_outsider_cannot_download_attached_private_media(self):
        media = self._create_attached_media()
        self.client.force_authenticate(self.outsider)

        response = self.client.get(f"/api/media/{media.uuid}/download/")

        self.assertEqual(response.status_code, 403)

    def _create_attached_media(self) -> UploadedMedia:
        chat = Chat.objects.create(chat_type=Chat.ChatType.DIRECT, creator=self.owner, members_count=2, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.owner, role=ChatMember.Role.OWNER, is_active=True)
        ChatMember.objects.create(chat=chat, user=self.member, role=ChatMember.Role.MEMBER, is_active=True)
        media = UploadedMedia.objects.create(
            owner=self.owner,
            original_name="note.txt",
            content_type="text/plain",
            size=5,
            media_kind=UploadedMedia.MediaKind.FILE,
            storage_provider=UploadedMedia.StorageProvider.LOCAL,
            status=UploadedMedia.Status.UPLOADED,
            is_public=False,
            file=SimpleUploadedFile("note.txt", b"hello", content_type="text/plain"),
        )
        message = Message.objects.create(chat=chat, sender=self.owner, message_type=Message.MessageType.FILE)
        MessageAttachment.objects.create(message=message, media=media)
        return media
