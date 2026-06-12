from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import BotCommand, BotMembership, BotProfile
from apps.chats.models import Chat, ChatMember
from apps.messaging.realtime_events import publish_realtime_event
from apps.messaging.serializers import MessageListSerializer

from .serializers import (
    BotAddToChatSerializer,
    BotCreateSerializer,
    BotMembershipSerializer,
    BotProfileSerializer,
    BotSendMessageSerializer,
    BotCommandResolveSerializer,
    BotUpdateSerializer,
    authenticate_bot_token,
    generate_bot_token,
)


def get_user_chat_or_404(user, chat_uuid):
    return get_object_or_404(
        Chat.objects.filter(
            uuid=chat_uuid,
            is_active=True,
            members__user=user,
            members__is_active=True,
        ).distinct()
    )


def user_can_manage_chat_bots(user, chat: Chat) -> bool:
    membership = ChatMember.objects.filter(chat=chat, user=user, is_active=True).first()
    if not membership:
        return False
    if chat.chat_type == Chat.ChatType.DIRECT:
        return True
    return membership.role in {ChatMember.Role.OWNER, ChatMember.Role.ADMIN}


def publish_bot_message(message, request):
    message = (
        message.__class__.objects.select_related("sender", "reply_to", "reply_to__sender")
        .prefetch_related("receipts", "attachments__media")
        .get(id=message.id)
    )
    data = MessageListSerializer(message, context={"request": request}).data
    publish_realtime_event(
        "message:new",
        str(message.chat.uuid),
        {
            "message": data,
            "message_uuid": str(message.uuid),
            "chat_uuid": str(message.chat.uuid),
            "sender_uuid": str(message.sender.uuid),
            "client_uuid": str(message.client_uuid or ""),
            "message_type": message.message_type,
        },
    )
    return data


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


class BotListCreateAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_scope = "bots"

    def get(self, request):
        bots = BotProfile.objects.filter(owner=request.user).select_related("owner", "user").order_by("-created_at")
        return Response({"results": BotProfileSerializer(bots, many=True, context={"request": request}).data})

    def post(self, request):
        serializer = BotCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bot = serializer.save()
        data = BotProfileSerializer(bot, context={"request": request}).data
        data["token"] = serializer.generated_token
        return Response(data, status=status.HTTP_201_CREATED)


class BotDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_scope = "bots"

    def get_bot(self, request, bot_uuid):
        return get_object_or_404(BotProfile.objects.select_related("owner", "user"), uuid=bot_uuid, owner=request.user)

    def get(self, request, bot_uuid):
        bot = self.get_bot(request, bot_uuid)
        return Response(BotProfileSerializer(bot, context={"request": request}).data)

    def patch(self, request, bot_uuid):
        bot = self.get_bot(request, bot_uuid)
        serializer = BotUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        bot = serializer.update(bot, serializer.validated_data)
        return Response(BotProfileSerializer(bot, context={"request": request}).data)

    def delete(self, request, bot_uuid):
        bot = self.get_bot(request, bot_uuid)
        bot.is_active = False
        bot.save(update_fields=["is_active", "updated_at"])
        bot.memberships.filter(is_active=True).update(is_active=False, updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class BotRotateTokenAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "bots"

    def post(self, request, bot_uuid):
        bot = get_object_or_404(BotProfile, uuid=bot_uuid, owner=request.user, is_active=True)
        token = generate_bot_token()
        bot.token_hash = make_password(token)
        bot.token_last_rotated_at = timezone.now()
        bot.save(update_fields=["token_hash", "token_last_rotated_at", "updated_at"])
        data = BotProfileSerializer(bot, context={"request": request}).data
        data["token"] = token
        return Response(data, status=status.HTTP_200_OK)


class ChatBotListCreateAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BotAddToChatSerializer
    throttle_scope = "bots"

    def get_chat(self, request, chat_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if not user_can_manage_chat_bots(request.user, chat):
            raise PermissionDenied("You cannot manage bots in this chat")
        return chat

    def get(self, request, chat_uuid):
        chat = self.get_chat(request, chat_uuid)
        memberships = chat.bot_memberships.filter(is_active=True).select_related("bot", "bot__owner", "bot__user")
        serializer = BotMembershipSerializer(memberships, many=True, context={"request": request})
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, chat_uuid):
        chat = self.get_chat(request, chat_uuid)
        serializer = self.get_serializer(data=request.data, context={"request": request, "chat": chat})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(BotMembershipSerializer(membership, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ChatBotDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "bots"

    def delete(self, request, chat_uuid, bot_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if not user_can_manage_chat_bots(request.user, chat):
            return Response({"detail": "You cannot manage bots in this chat"}, status=status.HTTP_403_FORBIDDEN)
        membership = get_object_or_404(BotMembership, chat=chat, bot__uuid=bot_uuid, is_active=True)
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        if membership.bot.user_id:
            ChatMember.objects.filter(chat=chat, user=membership.bot.user, is_active=True).update(
                is_active=False,
                updated_at=timezone.now(),
            )
            chat.members_count = chat.members.filter(is_active=True).count()
            chat.save(update_fields=["members_count", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class BotSendMessageAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "bot_send_message"

    def post(self, request):
        bot = authenticate_bot_token(request.headers.get("Authorization") or request.headers.get("X-Bot-Token"))
        if not bot or not bot.user:
            return Response({"detail": "Invalid bot token"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = BotSendMessageSerializer(data=request.data, context={"bot": bot})
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        message_data = publish_bot_message(message, request)
        return Response(message_data, status=status.HTTP_201_CREATED)
