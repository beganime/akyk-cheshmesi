from django.db import transaction
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.chats.models import Chat, ChatMember
from apps.common.pagination import ChatListPagination, MessageCursorPagination
from apps.messaging.models import Message, MessageReceipt
from apps.messaging.realtime_events import publish_realtime_event
from apps.messaging.serializers import (
    MessageCreateSerializer,
    MessageDeleteSerializer,
    MessageListSerializer,
    MessageUpdateSerializer,
)
from apps.users.contact_views import sync_contacts_from_chats

from .serializers import (
    ChatArchiveSerializer,
    ChatCreateSerializer,
    ChatDetailSerializer,
    ChatListSerializer,
    ChatMuteSerializer,
    ChatPinSerializer,
    ChatReadSerializer,
    ChatUpdateSerializer,
    DirectChatCreateSerializer,
    GroupAdminsSerializer,
    GroupChatCreateSerializer,
    GroupMembersSerializer,
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


def get_group_chat_for_user_or_404(user, chat_uuid):
    chat = get_user_chat_or_404(user, chat_uuid)
    if chat.chat_type != Chat.ChatType.GROUP:
        return None
    return chat


def get_group_admin_membership(user, chat):
    membership = ChatMember.objects.filter(chat=chat, user=user, is_active=True).first()
    if membership and membership.role in {ChatMember.Role.OWNER, ChatMember.Role.ADMIN}:
        return membership
    return None


def refresh_chat_members_count(chat):
    chat.members_count = chat.members.filter(is_active=True).count()
    chat.save(update_fields=["members_count", "updated_at"])
    return chat


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


def serialize_message_for_realtime(message, request):
    message = (
        Message.objects.select_related("sender", "reply_to", "reply_to__sender")
        .prefetch_related("receipts", "attachments__media")
        .get(id=message.id)
    )
    return MessageListSerializer(message, context={"request": request}).data


class ChatListAPIView(generics.ListAPIView):
    serializer_class = ChatListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatListPagination

    def get_queryset(self):
        request_user = self.request.user
        sync_contacts_from_chats(request_user)

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

    def post(self, request, *args, **kwargs):
        serializer = ChatCreateSerializer(data=request.data, context={"request": request})
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


class ChatRetrieveAPIView(generics.GenericAPIView):
    serializer_class = ChatDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
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

    def get_object(self):
        return get_object_or_404(self.get_queryset(), uuid=self.kwargs["chat_uuid"])

    def get(self, request, *args, **kwargs):
        chat = self.get_object()
        serializer = self.get_serializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        chat = self.get_object()
        serializer = ChatUpdateSerializer(
            data=request.data,
            context={"request": request, "chat": chat},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        chat = serializer.save()
        output = ChatDetailSerializer(chat, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        chat = self.get_object()
        membership = chat.members.filter(user=request.user, is_active=True).first()
        if chat.chat_type != Chat.ChatType.GROUP:
            return Response({"detail": "Only group chats can be deleted"}, status=status.HTTP_400_BAD_REQUEST)
        if not membership or membership.role != ChatMember.Role.OWNER:
            return Response({"detail": "Only group owner can delete the group"}, status=status.HTTP_403_FORBIDDEN)

        chat.is_active = False
        chat.save(update_fields=["is_active", "updated_at"])
        chat.members.filter(is_active=True).update(is_active=False, updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupMembersAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GroupMembersSerializer

    def post(self, request, chat_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if chat.chat_type != Chat.ChatType.GROUP:
            return Response({"detail": "Members can be managed only in group chats"}, status=status.HTTP_400_BAD_REQUEST)
        if not get_group_admin_membership(request.user, chat):
            return Response({"detail": "Only group admins can add members"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            for user in serializer.validated_data["users"]:
                membership, created = ChatMember.objects.get_or_create(
                    chat=chat,
                    user=user,
                    defaults={
                        "role": ChatMember.Role.MEMBER,
                        "is_active": True,
                        "can_send_messages": True,
                    },
                )
                if not created and not membership.is_active:
                    membership.is_active = True
                    membership.can_send_messages = True
                    membership.save(update_fields=["is_active", "can_send_messages", "updated_at"])
            refresh_chat_members_count(chat)

        output = ChatDetailSerializer(chat, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class GroupMemberDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, chat_uuid, user_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if chat.chat_type != Chat.ChatType.GROUP:
            return Response({"detail": "Members can be managed only in group chats"}, status=status.HTTP_400_BAD_REQUEST)

        actor_membership = get_group_admin_membership(request.user, chat)
        if not actor_membership:
            return Response({"detail": "Only group admins can remove members"}, status=status.HTTP_403_FORBIDDEN)

        target = get_object_or_404(ChatMember, chat=chat, user__uuid=user_uuid, is_active=True)
        if target.role == ChatMember.Role.OWNER:
            return Response({"detail": "Group owner cannot be removed"}, status=status.HTTP_400_BAD_REQUEST)
        if actor_membership.role != ChatMember.Role.OWNER and target.role == ChatMember.Role.ADMIN:
            return Response({"detail": "Only owner can remove admins"}, status=status.HTTP_403_FORBIDDEN)

        target.is_active = False
        target.save(update_fields=["is_active", "updated_at"])
        refresh_chat_members_count(chat)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupAdminsAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GroupAdminsSerializer

    def post(self, request, chat_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if chat.chat_type != Chat.ChatType.GROUP:
            return Response({"detail": "Admins can be managed only in group chats"}, status=status.HTTP_400_BAD_REQUEST)

        actor_membership = chat.members.filter(user=request.user, is_active=True).first()
        if not actor_membership or actor_membership.role != ChatMember.Role.OWNER:
            return Response({"detail": "Only group owner can assign admins"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            for user in serializer.validated_data["users"]:
                membership, _ = ChatMember.objects.get_or_create(
                    chat=chat,
                    user=user,
                    defaults={
                        "role": ChatMember.Role.ADMIN,
                        "is_active": True,
                        "can_send_messages": True,
                    },
                )
                if membership.role != ChatMember.Role.OWNER:
                    membership.role = ChatMember.Role.ADMIN
                membership.is_active = True
                membership.can_send_messages = True
                membership.save(update_fields=["role", "is_active", "can_send_messages", "updated_at"])
            refresh_chat_members_count(chat)

        output = ChatDetailSerializer(chat, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class GroupLeaveAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_uuid):
        chat = get_user_chat_or_404(request.user, chat_uuid)
        if chat.chat_type != Chat.ChatType.GROUP:
            return Response({"detail": "Only group chats can be left"}, status=status.HTTP_400_BAD_REQUEST)

        membership = get_object_or_404(ChatMember, chat=chat, user=request.user, is_active=True)

        with transaction.atomic():
            if membership.role == ChatMember.Role.OWNER:
                replacement = (
                    chat.members.filter(is_active=True)
                    .exclude(user=request.user)
                    .order_by(
                        F("role").asc(nulls_last=True),
                        "joined_at",
                    )
                    .first()
                )
                if replacement:
                    replacement.role = ChatMember.Role.OWNER
                    replacement.save(update_fields=["role", "updated_at"])
                else:
                    chat.is_active = False
                    chat.save(update_fields=["is_active", "updated_at"])

            membership.is_active = False
            membership.save(update_fields=["is_active", "updated_at"])
            refresh_chat_members_count(chat)

        return Response({"detail": "You left the group", "chat_uuid": str(chat.uuid)}, status=status.HTTP_200_OK)


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

        output_data = serialize_message_for_realtime(message, request)
        response_status = (
            status.HTTP_200_OK if getattr(serializer, "was_existing", False) else status.HTTP_201_CREATED
        )

        publish_realtime_event(
            "message_persisted",
            str(chat.uuid),
            {
                "message": output_data,
                "message_uuid": str(message.uuid),
                "chat_uuid": str(chat.uuid),
                "sender_uuid": str(message.sender.uuid),
                "client_uuid": str(message.client_uuid or ""),
                "message_type": message.message_type,
                "persisted_status": "duplicate" if getattr(serializer, "was_existing", False) else "saved",
            },
        )
        publish_realtime_event(
            "message:new",
            str(chat.uuid),
            {
                "message": output_data,
                "message_uuid": str(message.uuid),
                "chat_uuid": str(chat.uuid),
                "sender_uuid": str(message.sender.uuid),
                "client_uuid": str(message.client_uuid or ""),
                "message_type": message.message_type,
            },
        )

        return Response(output_data, status=response_status)


class ChatMessageDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_message(self):
        return get_user_message_or_404(
            self.request.user,
            self.kwargs["chat_uuid"],
            self.kwargs["message_uuid"],
        )

    def get(self, request, *args, **kwargs):
        message = self.get_message()
        output = MessageListSerializer(message, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        message = self.get_message()
        serializer = MessageUpdateSerializer(
            data=request.data,
            context={"request": request, "message": message},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        output = MessageListSerializer(message, context={"request": request})
        publish_realtime_event(
            "message:edit",
            str(message.chat.uuid),
            {
                "message": output.data,
                "message_uuid": str(message.uuid),
                "chat_uuid": str(message.chat.uuid),
                "sender_uuid": str(message.sender.uuid),
            },
        )
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
            publish_realtime_event(
                "message:delete",
                str(message.chat.uuid),
                {
                    "message": output.data,
                    "message_uuid": str(message.uuid),
                    "chat_uuid": str(message.chat.uuid),
                    "delete_for": "everyone",
                    "deleted_by_uuid": str(request.user.uuid),
                },
            )
            return Response(
                {
                    "detail": "Message deleted for everyone",
                    "delete_for": "everyone",
                    "message": output.data,
                },
                status=status.HTTP_200_OK,
            )

        publish_realtime_event(
            "message:delete",
            str(message.chat.uuid),
            {
                "message_uuid": str(message.uuid),
                "chat_uuid": str(message.chat.uuid),
                "delete_for": "me",
                "deleted_by_uuid": str(request.user.uuid),
            },
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
