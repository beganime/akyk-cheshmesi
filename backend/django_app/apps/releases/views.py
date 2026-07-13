from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET
from rest_framework import generics, permissions

from .models import AppRelease
from .serializers import AppReleaseSerializer


class AppReleaseListAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AppReleaseSerializer

    def get_queryset(self):
        queryset = AppRelease.objects.filter(is_active=True, is_public=True)
        platform = self.request.query_params.get("platform", "").strip().lower()
        channel = self.request.query_params.get("channel", "").strip().lower()

        if platform:
            queryset = queryset.filter(platform=platform)
        if channel:
            queryset = queryset.filter(channel=channel)

        return queryset


@require_GET
def app_release_download(request, release_uuid):
    queryset = AppRelease.objects.filter(package_file__isnull=False)
    if not request.user.is_staff:
        queryset = queryset.filter(is_active=True, is_public=True)
    release = get_object_or_404(queryset, uuid=release_uuid)
    if not release.package_file.name:
        return HttpResponse(status=404)

    filename = Path(release.package_file.name).name
    content_type = "application/vnd.android.package-archive"
    if getattr(settings, "MEDIA_USE_X_ACCEL_REDIRECT", False):
        internal_prefix = str(getattr(settings, "MEDIA_X_ACCEL_PREFIX", "/_protected_media/")).rstrip("/")
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = quote(
            f"{internal_prefix}/{release.package_file.name.lstrip('/')}",
            safe="/",
        )
        response["Content-Disposition"] = content_disposition_header(True, filename)
        if release.file_size_bytes:
            response["Content-Length"] = str(release.file_size_bytes)
        return response

    return FileResponse(
        release.package_file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )
