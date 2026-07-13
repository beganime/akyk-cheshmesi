import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AppRelease


class AppReleaseTests(TestCase):
    def build_release(self, **overrides):
        values = {
            "version": "1.2.3",
            "build_number": "123",
            "platform": AppRelease.Platform.ANDROID,
            "channel": AppRelease.ReleaseChannel.PRODUCTION,
            "store_status": AppRelease.StoreStatus.LIVE,
            "released_at": timezone.now(),
            "is_active": True,
            "is_public": True,
        }
        values.update(overrides)
        return AppRelease(**values)

    @override_settings(APP_RELEASE_MAX_UPLOAD_SIZE_BYTES=2)
    def test_apk_size_limit_is_validated(self):
        release = self.build_release(
            package_file=SimpleUploadedFile(
                "akyl.apk",
                b"apk",
                content_type="application/vnd.android.package-archive",
            )
        )

        with self.assertRaises(ValidationError) as context:
            release.full_clean()

        self.assertIn("package_file", context.exception.message_dict)

    @override_settings(MEDIA_USE_X_ACCEL_REDIRECT=True, MEDIA_X_ACCEL_PREFIX="/_protected_media/")
    def test_public_apk_uses_streaming_nginx_download(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            release = self.build_release(
                package_file=SimpleUploadedFile(
                    "akyl.apk",
                    b"apk-content",
                    content_type="application/vnd.android.package-archive",
                )
            )
            release.full_clean()
            release.save()

            url = reverse("app-release-download", kwargs={"release_uuid": release.uuid})
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/vnd.android.package-archive")
            self.assertTrue(response["X-Accel-Redirect"].endswith("/app_packages/android/akyl.apk"))
            self.assertEqual(response["Content-Length"], str(len(b"apk-content")))

            api_response = self.client.get(reverse("app-releases-list"))
            self.assertEqual(api_response.status_code, 200)
            item = api_response.json()[0]
            self.assertTrue(item["package_url"].endswith(url))
            self.assertEqual(item["resolved_download_url"], item["package_url"])

    @override_settings(MEDIA_USE_X_ACCEL_REDIRECT=True)
    def test_private_release_is_available_only_to_staff(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            release = self.build_release(
                is_public=False,
                package_file=SimpleUploadedFile("draft.apk", b"draft-apk"),
            )
            release.save()
            url = reverse("app-release-download", kwargs={"release_uuid": release.uuid})
            self.assertEqual(self.client.get(url).status_code, 404)

            staff = get_user_model().objects.create_user(
                email="release-admin@example.com",
                username="release-admin",
                password="test-password",
                is_staff=True,
                is_active=True,
                registration_completed=True,
            )
            self.client.force_login(staff)
            self.assertEqual(self.client.get(url).status_code, 200)
