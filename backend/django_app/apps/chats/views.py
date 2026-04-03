from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.chats.models import Chat, ChatMember
from apps.common.pagination import ChatListPagination, MessageCursorPagination
from apps.messaging.models import Message, MessageReceipt
from apps.messaging.serializers import (
    MessageCreateSerializer,
    MessageDeleteSerializer,
    MessageListSerializer,
    MessageUpdateSerializer,
)

from .serializers import (
    ChatArchiveSerializer,
    ChatDetailSerializer,
    ChatListSerializer,
    ChatMuteSerializer,
    ChatPinSerializer,
    ChatReadSerializer,
    DirectChatCreateSerializer,
    GroupChatCreateSerializer,
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


def get_user_membership_or_404(user, chat_uuid):
    return get_object_or_404(
        ChatMember.objects.select_related("chat", "user").filter(
            chat__uuid=chat_uuid,
            chat__is_active=True,
            user=user,
            is_active=True,
        )
    )


def get_user_message_or_404(user, chat_uuid, message_uuid):
    return get_object_or_404(
        Message.objects.select_related("sender", "reply_to", "reply_to__sender")
        .prefetch_related("receipts", "attachments__media")
        .filter(
            uuid=message_uuid,
            chat__uuid=chat_uuid,
            chat__is_active=True,
            chat__members__user=user,
            chat__members__is_active=True,
        )
        .distinct()
    )


class ChatListAPIView(generics.ListAPIView):
    serializer_class = ChatListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatListPagination

    def get_queryset(self):
        request_user = self.request.user

        last_message_qs = Message.objects.filter(chat=OuterRef("pk")).order_by("-created_at")
        current_member_qs = ChatMember.objects.filter(
            chat=OuterRef("pk"),
            user=request_user,
            is_active=True,
        )
        active_members_qs = ChatMember.objects.filter(is_active=True).select_related("user")

        queryset = (
            Chat.objects.filter(
                is_active=True,
                members__user=request_user,
                members__is_active=True,
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=active_members_qs,
                    to_attr="prefetched_active_members",
                )
            )
            .annotate(
                current_member_last_read_at=Subquery(current_member_qs.values("last_read_at")[:1]),
                current_member_is_muted=Subquery(current_member_qs.values("is_muted")[:1]),
                current_member_is_pinned=Subquery(current_member_qs.values("is_pinned")[:1]),
                current_member_pinned_at=Subquery(current_member_qs.values("pinned_at")[:1]),
                current_member_is_archived=Subquery(current_member_qs.values("is_archived")[:1]),
                last_message_uuid=Subquery(last_message_qs.values("uuid")[:1]),
                last_message_text=Subquery(last_message_qs.values("text")[:1]),
                last_message_type=Subquery(last_message_qs.values("message_type")[:1]),
            )
            .annotate(
                unread_count_value=Count(
                    "messages",
                    filter=(
                        (
                            Q(messages__created_at__gt=F("current_member_last_read_at"))
                            | Q(current_member_last_read_at__isnull=True)
                        )
                        & ~Q(messages__sender=request_user)
                        & Q(messages__is_deleted=False)
                    ),
                    distinct=True,
                )
            )
        )

        archived = (self.request.query_params.get("archived") or "").strip().lower()
        if archived in {"1", "true", "yes"}:
            queryset = queryset.filter(current_member_is_archived=True)
        else:
            queryset = queryset.filter(
                Q(current_member_is_archived=False) | Q(current_member_is_archived__isnull=True)
            )

        pinned = (self.request.query_params.get("pinned") or "").strip().lower()
        if pinned in {"1", "true", "yes"}:
            queryset = queryset.filter(current_member_is_pinned=True)

        return queryset.order_by(
            F("current_member_is_pinned").desc(nulls_last=True),
            F("current_member_pinned_at").desc(nulls_last=True),
            F("last_message_at").desc(nulls_last=True),
            "-created_at",
        )


class DirectChatCreateAPIView(generics.CreateAPIView):
    serializer_class = DirectChatCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat = serializer.save()
        output = ChatDetailSerializer(chat, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class GroupChatCreateAPIView(generics.CreateAPIView):
    serializer_class = GroupChatCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat = serializer.save()
        chat = (
            Chat.objects.filter(id=chat.id)
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=ChatMember.objects.filter(is_active=True).select_related("user"),
                    to_attr="prefetched_active_members",
                )
            )
            .first()
        )
        output = ChatDetailSerializer(chat, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class ChatRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = ChatDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "chat_uuid"

    def get_queryset(self):
        return (
            Chat.objects.filter(
                is_active=True,
                members__user=self.request.user,
                members__is_active=True,
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=ChatMember.objects.filter(is_active=True).select_related("user"),
                    to_attr="prefetched_active_members",
                )
            )
        )


class ChatMessagesAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessageCursorPagination

    def get_chat(self):
        return get_user_chat_or_404(self.request.user, self.kwargs["chat_uuid"])

    def get(self, request, *args, **kwargs):
        chat = self.get_chat()

        MessageReceipt.objects.filter(
            message__chat=chat,
            user=request.user,
            delivered_at__isnull=True,
        ).update(delivered_at=timezone.now())

        queryset = (
            Message.objects.filter(chat=chat)
            .exclude(user_states__user=request.user, user_states__is_hidden=True)
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("receipts", "attachments__media")
            .order_by("-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MessageListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        chat = self.get_chat()
        serializer = MessageCreateSerializer(
            data=request.data,
            context={"request": request, "chat": chat},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        output = MessageListSerializer(message, context={"request": request})
        response_status = (
            status.HTTP_200_OK if getattr(serializer, "was_existing", False) else status.HTTP_201_CREATED
        )
        return Response(output.data, status=response_status)


class ChatMessageDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_message(self):
        return get_user_message_or_404(
            self.request.user,
            self.kwargs["chat_uuid"],
            self.kwargs["message_uuid"],
        )

    def patch(self, request, *args, **kwargs):
        message = self.get_message()
        serializer = MessageUpdateSerializer(
            data=request.data,
            context={"request": request, "message": message},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        output = MessageListSerializer(message, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        message = self.get_message()
        serializer = MessageDeleteSerializer(
            data=request.data or {},
            context={"request": request, "message": message},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        if result["delete_for"] == MessageDeleteSerializer.DELETE_FOR_EVERYONE:
            output = MessageListSerializer(result["message"], context={"request": request})
            return Response(
                {
                    "detail": "Message deleted for everyone",
                    "delete_for": "everyone",
                    "message": output.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": "Message deleted for current user",
                "delete_for": "me",
                "message_uuid": str(message.uuid),
            },
            status=status.HTTP_200_OK,
        )


class ChatMarkReadAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatReadSerializer

    def get_chat(self):
        return get_user_chat_or_404(self.request.user, self.kwargs["chat_uuid"])

    def post(self, request, *args, **kwargs):
        chat = self.get_chat()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        message_uuid = serializer.validated_data.get("message_uuid")

        receipt_filters = Q(message__chat=chat, user=request.user)

        if message_uuid:
            target_message = get_object_or_404(Message, chat=chat, uuid=message_uuid)
            receipt_filters &= Q(message__created_at__lte=target_message.created_at)

        MessageReceipt.objects.filter(receipt_filters).update(
            delivered_at=now,
            read_at=now,
        )

        ChatMember.objects.filter(
            chat=chat,
            user=request.user,
            is_active=True,
        ).update(last_read_at=now)

        return Response(
            {
                "detail": "Messages marked as read",
                "chat_uuid": str(chat.uuid),
                "read_at": now,
            },
            status=status.HTTP_200_OK,
        )


class ChatPinAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatPinSerializer

    def post(self, request, *args, **kwargs):
        membership = get_user_membership_or_404(request.user, self.kwargs["chat_uuid"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update_membership(membership, "is_pinned", serializer.validated_data["is_pinned"])

        return Response(
            {
                "detail": "Chat pin state updated",
                "chat_uuid": str(membership.chat.uuid),
                "is_pinned": membership.is_pinned,
                "pinned_at": membership.pinned_at,
            },
            status=status.HTTP_200_OK,
        )


class ChatArchiveAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatArchiveSerializer

    def post(self, request, *args, **kwargs):
        membership = get_user_membership_or_404(request.user, self.kwargs["chat_uuid"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update_membership(membership, "is_archived", serializer.validated_data["is_archived"])

        return Response(
            {
                "detail": "Chat archive state updated",
                "chat_uuid": str(membership.chat.uuid),
                "is_archived": membership.is_archived,
                "archived_at": membership.archived_at,
            },
            status=status.HTTP_200_OK,
        )


class ChatMuteAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatMuteSerializer

    def post(self, request, *args, **kwargs):
        membership = get_user_membership_or_404(request.user, self.kwargs["chat_uuid"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update_membership(membership, "is_muted", serializer.validated_data["is_muted"])

        return Response(
            {
                "detail": "Chat mute state updated",
                "chat_uuid": str(membership.chat.uuid),
                "is_muted": membership.is_muted,
            },
            status=status.HTTP_200_OK,
        )