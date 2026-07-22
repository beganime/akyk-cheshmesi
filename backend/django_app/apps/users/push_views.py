from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .push_serializers import (
    BrowserPushSubscriptionDeleteSerializer,
    BrowserPushSubscriptionSerializer,
    PushTokenDeleteSerializer,
    PushTokenSerializer,
    PushTokenUpsertSerializer,
)


class PushTokenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushTokenUpsertSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        push_token = serializer.save()

        return Response(
            {
                "detail": "Push token registered",
                "push_token": PushTokenSerializer(push_token).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        serializer = PushTokenDeleteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        deactivated_count = serializer.deactivate()

        return Response(
            {
                "detail": "Push token deactivated",
                "deactivated_count": deactivated_count,
            },
            status=status.HTTP_200_OK,
        )


class BrowserPushConfigAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        public_key = (getattr(settings, "WEB_PUSH_VAPID_PUBLIC_KEY", "") or "").strip()
        private_key = (getattr(settings, "WEB_PUSH_VAPID_PRIVATE_KEY", "") or "").strip()
        return Response(
            {
                "enabled": bool(getattr(settings, "WEB_PUSH_ENABLED", False) and public_key and private_key),
                "public_key": public_key,
            },
            status=status.HTTP_200_OK,
        )


class BrowserPushSubscriptionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BrowserPushSubscriptionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        return Response(
            {
                "detail": "Browser push subscription registered",
                "subscription_uuid": str(subscription.uuid),
                "is_active": subscription.is_active,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        serializer = BrowserPushSubscriptionDeleteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "detail": "Browser push subscription deactivated",
                "deactivated_count": serializer.deactivate(),
            },
            status=status.HTTP_200_OK,
        )
