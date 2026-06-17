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
