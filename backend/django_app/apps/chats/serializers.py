from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.chats.models import Chat, ChatMember
from apps.chats.utils import build_direct_chat_key
from apps.users.public_serializers import UserShortSerializer

User = get_user_model()


class ChatMemberSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = ChatMember
        fields = (
            "uuid",
            "role",
            "is_active",
            "is_muted",
            "is_pinned",
            "pinned_at",
            "is_archived",
            "archived_at",
            "can_send_messages",
            "last_read_at",
            "joined_at",
            "user",
        )


class ChatListSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    peer_user = serializers.SerializerMethodField()
    display_title = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    has_unread = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    pinned_at = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    last_read_at = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = (
            "uuid",
            "type",
            "chat_type",
            "title",
            "description",
            "avatar",
            "owner",
            "admins",
            "display_title",
            "peer_user",
            "members_count",
            "last_message_at",
            "is_public",
            "members",
            "last_message",
            "unread_count",
            "has_unread",
            "is_pinned",
            "pinned_at",
            "is_archived",
            "is_muted",
            "last_read_at",
            "created_at",
            "updated_at",
        )

    def _get_current_membership(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        membership = getattr(obj, "current_membership_obj", None)
        if membership is not None:
            return membership

        return obj.members.filter(user=request.user, is_active=True).first()

    def _get_active_members(self, obj):
        members = getattr(obj, "prefetched_active_members", None)
        if members is None:
            members = obj.members.filter(is_active=True).select_related("user")
        return members

    def get_type(self, obj):
        return "private" if obj.chat_type == Chat.ChatType.DIRECT else "group"

    def get_owner(self, obj):
        owner = next(
            (member.user for member in self._get_active_members(obj) if member.role == ChatMember.Role.OWNER),
            None,
        )
        return UserShortSerializer(owner, context=self.context).data if owner else None

    def get_admins(self, obj):
        if obj.chat_type != Chat.ChatType.GROUP:
            return []
        admins = [
            member.user
            for member in self._get_active_members(obj)
            if member.role in {ChatMember.Role.OWNER, ChatMember.Role.ADMIN}
        ]
        return UserShortSerializer(admins, many=True, context=self.context).data

    def get_members(self, obj):
        return ChatMemberSerializer(
            self._get_active_members(obj),
            many=True,
            context=self.context,
        ).data

    def get_peer_user(self, obj):
        request = self.context.get("request")
        if not request or obj.chat_type != Chat.ChatType.DIRECT:
            return None

        for member in self._get_active_members(obj):
            if member.user_id != request.user.id:
                return UserShortSerializer(member.user, context=self.context).data
        return None

    def get_display_title(self, obj):
        if obj.chat_type == Chat.ChatType.GROUP:
            return obj.title or "Group chat"

        peer = self.get_peer_user(obj)
        if not peer:
            return "Direct chat"

        full_name = peer.get("full_name") or ""
        return full_name or peer.get("username") or "Direct chat"

    def get_last_message(self, obj):
        last_message_uuid = getattr(obj, "last_message_uuid", None)
        if not last_message_uuid:
            return None

        message_type = getattr(obj, "last_message_type", "text") or "text"
        text = getattr(obj, "last_message_text", "") or ""
        preview = text
        if not preview:
            preview_map = {
                "image": "Photo",
                "video": "Video",
                "audio": "Audio",
                "video_note": "Video note",
                "file": "File",
                "sticker": "Sticker",
                "system": "System message",
            }
            preview = preview_map.get(message_type, "Message")

        return {
            "uuid": str(last_message_uuid),
            "text": text,
            "preview": preview,
            "message_type": message_type,
            "created_at": obj.last_message_at,
        }

    def get_unread_count(self, obj):
        annotated = getattr(obj, "unread_count_value", None)
        if annotated is not None:
            return int(annotated)

        request = self.context.get("request")
        membership = self._get_current_membership(obj)
        if not request or not membership:
            return 0

        queryset = obj.messages.exclude(sender_id=request.user.id).filter(is_deleted=False)
        if membership.last_read_at:
            queryset = queryset.filter(created_at__gt=membership.last_read_at)
        return queryset.count()

    def get_has_unread(self, obj):
        return self.get_unread_count(obj) > 0

    def get_is_pinned(self, obj):
        annotated = getattr(obj, "current_member_is_pinned", None)
        if annotated is not None:
            return bool(annotated)
        membership = self._get_current_membership(obj)
        return bool(membership and membership.is_pinned)

    def get_pinned_at(self, obj):
        annotated = getattr(obj, "current_member_pinned_at", None)
        if annotated is not None:
            return annotated
        membership = self._get_current_membership(obj)
        return membership.pinned_at if membership else None

    def get_is_archived(self, obj):
        annotated = getattr(obj, "current_member_is_archived", None)
        if annotated is not None:
            return bool(annotated)
        membership = self._get_current_membership(obj)
        return bool(membership and membership.is_archived)

    def get_is_muted(self, obj):
        annotated = getattr(obj, "current_member_is_muted", None)
        if annotated is not None:
            return bool(annotated)
        membership = self._get_current_membership(obj)
        return bool(membership and membership.is_muted)

    def get_last_read_at(self, obj):
        annotated = getattr(obj, "current_member_last_read_at", None)
        if annotated is not None:
            return annotated
        membership = self._get_current_membership(obj)
        return membership.last_read_at if membership else None


class ChatDetailSerializer(ChatListSerializer):
    class Meta(ChatListSerializer.Meta):
        fields = ChatListSerializer.Meta.fields


class DirectChatCreateSerializer(serializers.Serializer):
    peer_uuid = serializers.UUIDField()

    def validate_peer_uuid(self, value):
        request = self.context["request"]
        if str(value) == str(request.user.uuid):
            raise serializers.ValidationError("You cannot create a direct chat with yourself")

        user = User.objects.filter(
            uuid=value,
            is_active=True,
            is_email_verified=True,
            registration_completed=True,
        ).first()

        if not user:
            raise serializers.ValidationError("User not found")

        self.peer_user = user
        return value

    def create(self, validated_data):
        request = self.context["request"]
        current_user = request.user
        peer_user = self.peer_user
        direct_key = build_direct_chat_key(current_user.uuid, peer_user.uuid)

        with transaction.atomic():
            chat = Chat.objects.select_for_update().filter(direct_key=direct_key).first()
            if not chat:
                chat = Chat.objects.create(
                    chat_type=Chat.ChatType.DIRECT,
                    direct_key=direct_key,
                    creator=current_user,
                    members_count=2,
                    is_active=True,
                )

            ChatMember.objects.update_or_create(
                chat=chat,
                user=current_user,
                defaults={
                    "role": ChatMember.Role.OWNER,
                    "is_active": True,
                    "can_send_messages": True,
                },
            )
            ChatMember.objects.update_or_create(
                chat=chat,
                user=peer_user,
                defaults={
                    "role": ChatMember.Role.MEMBER,
                    "is_active": True,
                    "can_send_messages": True,
                },
            )

            active_members_count = chat.members.filter(is_active=True).count()
            if chat.members_count != active_members_count or not chat.is_active:
                chat.members_count = active_members_count
                chat.is_active = True
                chat.save(update_fields=["members_count", "is_active", "updated_at"])

        return chat


class GroupChatCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    member_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        member_uuids = attrs.get("member_uuids", [])
        users = list(
            User.objects.filter(
                uuid__in=member_uuids,
                is_active=True,
                is_email_verified=True,
                registration_completed=True,
            )
        )

        found_uuids = {str(user.uuid) for user in users}
        requested_uuids = {str(value) for value in member_uuids}
        missing = requested_uuids - found_uuids
        if missing:
            raise serializers.ValidationError(
                {"member_uuids": f"Some users were not found: {', '.join(sorted(missing))}"}
            )

        self.group_members = users
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        current_user = request.user
        title = validated_data["title"].strip()
        description = validated_data.get("description", "").strip()

        with transaction.atomic():
            chat = Chat.objects.create(
                chat_type=Chat.ChatType.GROUP,
                title=title,
                description=description,
                creator=current_user,
                is_active=True,
            )

            ChatMember.objects.create(
                chat=chat,
                user=current_user,
                role=ChatMember.Role.OWNER,
                is_active=True,
                can_send_messages=True,
            )

            created_user_ids = {current_user.id}
            bulk_members = []
            for user in self.group_members:
                if user.id in created_user_ids:
                    continue
                created_user_ids.add(user.id)
                bulk_members.append(
                    ChatMember(
                        chat=chat,
                        user=user,
                        role=ChatMember.Role.MEMBER,
                        is_active=True,
                        can_send_messages=True,
                    )
                )

            if bulk_members:
                ChatMember.objects.bulk_create(bulk_members)

            chat.members_count = chat.members.filter(is_active=True).count()
            chat.save(update_fields=["members_count", "updated_at"])

        return chat


class ChatCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[("private", "Private"), ("group", "Group")])
    peer_uuid = serializers.UUIDField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    member_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        if attrs["type"] == "private" and not attrs.get("peer_uuid"):
            raise serializers.ValidationError({"peer_uuid": "Private chat requires peer_uuid"})
        if attrs["type"] == "group" and not (attrs.get("title") or "").strip():
            raise serializers.ValidationError({"title": "Group chat requires title"})
        return attrs

    def create(self, validated_data):
        if validated_data["type"] == "private":
            serializer = DirectChatCreateSerializer(
                data={"peer_uuid": validated_data["peer_uuid"]},
                context=self.context,
            )
        else:
            serializer = GroupChatCreateSerializer(
                data={
                    "title": validated_data.get("title", ""),
                    "description": validated_data.get("description", ""),
                    "member_uuids": validated_data.get("member_uuids", []),
                },
                context=self.context,
            )
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class ChatUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        chat = self.context["chat"]
        request = self.context["request"]
        if chat.chat_type != Chat.ChatType.GROUP:
            raise serializers.ValidationError("Only group chats can be updated")

        membership = chat.members.filter(user=request.user, is_active=True).first()
        if not membership or membership.role not in {ChatMember.Role.OWNER, ChatMember.Role.ADMIN}:
            raise serializers.ValidationError("Only group admins can update group info")

        if not attrs:
            raise serializers.ValidationError("Nothing to update")
        return attrs

    def save(self, **kwargs):
        chat = self.context["chat"]
        changed = []
        for field in ("title", "description", "avatar"):
            if field in self.validated_data:
                setattr(chat, field, self.validated_data[field])
                changed.append(field)
        if changed:
            changed.append("updated_at")
            chat.save(update_fields=changed)
        return chat


class GroupMembersSerializer(serializers.Serializer):
    member_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )
    user_uuid = serializers.UUIDField(required=False)

    def validate(self, attrs):
        member_uuids = list(attrs.get("member_uuids") or [])
        if attrs.get("user_uuid"):
            member_uuids.append(attrs["user_uuid"])
        if not member_uuids:
            raise serializers.ValidationError("At least one user_uuid/member_uuids value is required")

        users = list(
            User.objects.filter(
                uuid__in=member_uuids,
                is_active=True,
                is_email_verified=True,
                registration_completed=True,
            )
        )
        found_uuids = {str(user.uuid) for user in users}
        requested_uuids = {str(value) for value in member_uuids}
        missing = requested_uuids - found_uuids
        if missing:
            raise serializers.ValidationError(
                {"member_uuids": f"Some users were not found: {', '.join(sorted(missing))}"}
            )

        attrs["users"] = users
        return attrs


class GroupAdminsSerializer(GroupMembersSerializer):
    pass


class ChatReadSerializer(serializers.Serializer):
    message_uuid = serializers.UUIDField(required=False)


class BaseChatMembershipToggleSerializer(serializers.Serializer):
    def update_membership(self, membership, field_name: str, value: bool):
        now = timezone.now()

        setattr(membership, field_name, value)
        update_fields = [field_name, "updated_at"]

        if field_name == "is_pinned":
            membership.pinned_at = now if value else None
            update_fields.append("pinned_at")

        if field_name == "is_archived":
            membership.archived_at = now if value else None
            update_fields.append("archived_at")

        membership.save(update_fields=update_fields)
        return membership


class ChatPinSerializer(BaseChatMembershipToggleSerializer):
    is_pinned = serializers.BooleanField()


class ChatArchiveSerializer(BaseChatMembershipToggleSerializer):
    is_archived = serializers.BooleanField()


class ChatMuteSerializer(BaseChatMembershipToggleSerializer):
    is_muted = serializers.BooleanField()
