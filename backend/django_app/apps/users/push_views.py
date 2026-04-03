from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .push_serializers import PushTokenDeleteSerializer, PushTokenUpsertSerializer


class PushTokenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushTokenUpsertSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        push_token = serializer.save()

        return Response(
            {
                "detail": "Push token registered",
                "token": push_token.token,
                "provider": push_token.provider,
                "platform": push_token.platform,
                "is_active": push_token.is_active,
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