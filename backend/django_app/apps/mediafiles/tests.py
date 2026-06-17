import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.chats.models import Chat, ChatMember
from apps.mediafiles.models import MessageAttachment, UploadedMedia
from apps.messaging.models import Message


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="akyl-media-tests-")


def create_active_user(email: str, username: str):
    return get_user_model().objects.create_user(
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
class LocalMediaAPITests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="akyl-media-access-tests-")
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.owner = create_active_user("media-owner@example.com", "mediaowner")
        self.member = create_active_user("media-member@example.com", "mediamember")
        self.outsider = create_active_user("media-outsider@example.com", "mediaoutsider")

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_upload_local_media(self):
        self.client.force_authenticate(self.owner)
        file_obj = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")

        response = self.client.post("/api/v1/media/upload-local/", {"file": file_obj}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        media = UploadedMedia.objects.get(uuid=response.data["uuid"])
        self.assertEqual(media.storage_provider, UploadedMedia.StorageProvider.LOCAL)
        self.assertEqual(media.media_kind, UploadedMedia.MediaKind.FILE)
        self.assertIn("/api/media/", response.data["file_url"])

    def test_reject_dangerous_extension(self):
        self.client.force_authenticate(self.owner)
        file_obj = SimpleUploadedFile("payload.php", b"<?php echo 1;", content_type="text/plain")

        response = self.client.post("/api/v1/media/upload-local/", {"file": file_obj}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("extension", response.data["detail"])

    def test_outsider_cannot_download_attached_private_media(self):
        media = self._create_attached_media()
        self.client.force_authenticate(self.outsider)

        response = self.client.get(f"/api/v1/media/{media.uuid}/download/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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


@override_settings(
    USE_S3=False,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    MEDIA_MAX_UPLOAD_SIZE_BYTES=1024 * 1024,
    VIDEO_MAX_SIZE_MB=5,
    AUDIO_MAX_SIZE_MB=5,
)
class LocalMediaUploadStoryContractTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = create_active_user("story-user@example.com", "storyuser")
        self.client.force_authenticate(self.user)

    def make_image_upload(self, filename="story-image.jpg", size=(750, 429)):
        image = Image.new("RGB", size, color=(24, 120, 200))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/jpeg")

    def make_video_upload(self, filename="story-video.mp4"):
        return SimpleUploadedFile(filename, b"\x00\x00\x00\x18ftypmp42sample", content_type="video/mp4")

    def test_upload_local_image_multipart_accepts_string_fields(self):
        response = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": self.make_image_upload(),
                "is_public": "false",
                "width": "750",
                "height": "429",
                "mime_type": "image/jpeg",
                "original_name": "story-image.jpg",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["media_kind"], UploadedMedia.MediaKind.IMAGE)
        self.assertEqual(response.data["content_type"], "image/jpeg")
        self.assertFalse(response.data["is_public"])
        self.assertEqual(response.data["width"], 750)
        self.assertEqual(response.data["height"], 429)
        self.assertGreater(response.data["size_bytes"], 0)
        self.assertTrue(response.data["file_url"])
        self.assertTrue(response.data["thumbnail_url"])

    def test_upload_local_video_multipart_accepts_duration(self):
        response = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": self.make_video_upload(),
                "is_public": "false",
                "width": "750",
                "height": "429",
                "duration_seconds": "12",
                "media_kind": "video",
                "mime_type": "video/mp4",
                "original_name": "story-video.mp4",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["media_kind"], UploadedMedia.MediaKind.VIDEO)
        self.assertEqual(response.data["content_type"], "video/mp4")
        self.assertFalse(response.data["is_public"])
        self.assertEqual(response.data["width"], 750)
        self.assertEqual(response.data["height"], 429)
        self.assertEqual(response.data["duration_seconds"], 12)
        self.assertGreater(response.data["size_bytes"], 0)
        self.assertTrue(response.data["file_url"])

    def test_upload_local_without_file_returns_400(self):
        response = self.client.post(
            "/api/v1/media/upload-local/",
            {"is_public": "false", "width": "750", "height": "429"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_upload_local_unsupported_extension_returns_400(self):
        response = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": SimpleUploadedFile("unsupported.bin", b"sample", content_type="application/x-unknown"),
                "is_public": "false",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported content type", response.data["detail"])

    @override_settings(MEDIA_MAX_UPLOAD_SIZE_BYTES=5)
    def test_upload_local_too_large_returns_400(self):
        response = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": SimpleUploadedFile("big.jpg", b"x" * 32, content_type="image/jpeg"),
                "is_public": "false",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_create_image_story_with_uploaded_media_uuid_and_urls_in_list(self):
        upload = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": self.make_image_upload(),
                "is_public": "false",
                "width": "750",
                "height": "429",
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED, upload.data)

        create = self.client.post(
            "/api/v1/stories/",
            {"media_type": "image", "media_uuid": upload.data["uuid"], "caption": "optional"},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        self.assertEqual(create.data["media"]["uuid"], upload.data["uuid"])
        self.assertTrue(create.data["media"]["file_url"])
        self.assertTrue(create.data["media"]["thumbnail_url"])

        listing = self.client.get("/api/v1/stories/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK, listing.data)
        first = listing.data["results"][0]
        self.assertTrue(first["media"]["file_url"])
        self.assertTrue(first["media"]["thumbnail_url"])

        detail = self.client.get(f"/api/v1/stories/{create.data['uuid']}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertTrue(detail.data["media"]["file_url"])
        self.assertTrue(detail.data["media"]["thumbnail_url"])

    def test_create_video_story_with_uploaded_media_uuid(self):
        upload = self.client.post(
            "/api/v1/media/upload-local/",
            {
                "file": self.make_video_upload(),
                "is_public": "false",
                "width": "750",
                "height": "429",
                "duration_seconds": "12",
                "media_kind": "video",
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED, upload.data)

        create = self.client.post(
            "/api/v1/stories/",
            {"media_type": "video", "media_uuid": upload.data["uuid"], "caption": "optional"},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        self.assertEqual(create.data["media"]["uuid"], upload.data["uuid"])
        self.assertEqual(create.data["media"]["media_kind"], UploadedMedia.MediaKind.VIDEO)
        self.assertTrue(create.data["media"]["file_url"])
