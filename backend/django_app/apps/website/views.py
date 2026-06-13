from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import CompanyTeamMember, SiteSettings, SupportRequest
from .serializers import (
    CompanyTeamMemberSerializer,
    SiteSettingsSerializer,
    SupportRequestCreateSerializer,
)


class PublicSiteContentAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings = SiteSettings.objects.filter(is_published=True).order_by("-updated_at").first()
        team = CompanyTeamMember.objects.filter(is_active=True)

        return Response(
            {
                "settings": SiteSettingsSerializer(settings, context={"request": request}).data if settings else None,
                "team": CompanyTeamMemberSerializer(team, many=True, context={"request": request}).data,
            }
        )


class CompanyTeamListAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CompanyTeamMemberSerializer

    def get_queryset(self):
        queryset = CompanyTeamMember.objects.filter(is_active=True)
        team = self.request.query_params.get("team", "").strip()
        if team:
            queryset = queryset.filter(team=team)
        return queryset


class SupportRequestCreateAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "website_support"
    serializer_class = SupportRequestCreateSerializer

    def perform_create(self, serializer):
        request = self.request
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
        serializer.save(
            ip_address=ip_address or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
            source="website",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "ok": True,
                "message": "Заявка принята. Мы свяжемся с вами в ближайшее время.",
                "request": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )
