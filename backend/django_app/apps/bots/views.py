from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import BotCommand
from .serializers import BotCommandResolveSerializer


class BotCommandResolveAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BotCommandResolveSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        incoming = serializer.validated_data["text"].strip()
        if not incoming:
            return Response({"detail": "Empty command"}, status=status.HTTP_400_BAD_REQUEST)

        command = incoming.split()[0].lower()
        bot_command = (
            BotCommand.objects.select_related("bot")
            .filter(command=command, is_active=True, bot__is_active=True)
            .first()
        )
        if not bot_command:
            return Response({"matched": False, "response_text": ""}, status=status.HTTP_200_OK)

        return Response(
            {
                "matched": True,
                "bot": {"code": bot_command.bot.code, "title": bot_command.bot.title},
                "command": bot_command.command,
                "response_text": bot_command.response_text,
            },
            status=status.HTTP_200_OK,
        )
