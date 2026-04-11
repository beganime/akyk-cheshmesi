from django.utils import timezone
from rest_framework import serializers

from apps.mediafiles.models import MessageAttachment, UploadedMedia
from apps.mediafiles.serializers import MediaAttachmentBriefSerializer
from apps.messaging.models import Message, MessageReceipt, MessageUserState
from apps.users.public_serializers import UserShortSerializer

VIDEO_MAX_DURATION_SECONDS = 30
AUDIO_MAX_DURATION_SECONDS = 300


class ReplyMessageShortSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)

    class Meta:
        model = Message
        fields = (
            "uuid",
            "text",
            "message_type",
            "sender",
            "created_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["text"] = "Сообщение удалено"

        return data


class MessageListSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    reply_to = ReplyMessageShortSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    delivered_to_count = serializers.SerializerMethodField()
    read_by_count = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "uuid",
            "client_uuid",
            "message_type",
            "text",
            "reply_to",
            "metadata",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "sender",
            "is_own_message",
            "delivered_to_count",
            "read_by_count",
            "delivery_status",
            "attachments",
            "created_at",
            "updated_at",
        )

    def _get_receipts(self, obj):
        receipts = getattr(obj, "prefetched_receipts", None)
        if receipts is None:
            receipts = obj.receipts.all()
        return receipts

    def _get_attachments(self, obj):
        attachments = getattr(obj, "prefetched_attachments", None)
        if attachments is None:
            attachments = obj.attachments.select_related("media").all()
        return attachments

    def get_is_own_message(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.id == obj.sender_id)

    def get_delivered_to_count(self, obj):
        return sum(1 for receipt in self._get_receipts(obj) if receipt.delivered_at is not None)

    def get_read_by_count(self, obj):
        return sum(1 for receipt in self._get_receipts(obj) if receipt.read_at is not None)

    def get_delivery_status(self, obj):
        request = self.context.get("request")

        if not request or request.user.id != obj.sender_id:
            return None

        receipts = list(self._get_receipts(obj))
        if not receipts:
            return "sent"

        has_read = any(receipt.read_at is not None for receipt in receipts)
        if has_read:
            return "read"

        has_delivered = any(receipt.delivered_at is not None for receipt in receipts)
        if has_delivered:
            return "delivered"

        return "sent"

    def get_attachments(self, obj):
        if obj.is_deleted:
            return []

        media_items = [attachment.media for attachment in self._get_attachments(obj)]
        return MediaAttachmentBriefSerializer(media_items, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["text"] = "Сообщение удалено"
            data["metadata"] = {}
            data["attachments"] = []

        return data


class MessageCreateSerializer(serializers.Serializer):
    message_type = serializers.ChoiceField(
        choices=Message.MessageType.choices,
        default=Message.MessageType.TEXT,
    )
    text = serializers.CharField(required=False, allow_blank=True)
    reply_to_uuid = serializers.UUIDField(required=False)
    client_uuid = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False)
    attachment_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        chat = self.context["chat"]
        user = self.context["request"].user

        membership = chat.members.filter(user=user, is_active=True).first()
        if not membership:
            raise serializers.ValidationError("You are not a member of this chat")

        if not membership.can_send_messages:
            raise serializers.ValidationError("You are not allowed to send messages")

        message_type = attrs.get("message_type", Message.MessageType.TEXT)
        text = (attrs.get("text") or "").strip()
        reply_to_uuid = attrs.get("reply_to_uuid")

        if reply_to_uuid:
            reply_to = Message.objects.filter(chat=chat, uuid=reply_to_uuid).first()
            if not reply_to:
                raise serializers.ValidationError({"reply_to_uuid": "Reply message not found"})
            attrs["reply_to"] = reply_to

        attachment_uuid_values = attrs.get("attachment_uuids", []) or []
        uploaded_media = []

        if attachment_uuid_values:
            media_queryset = UploadedMedia.objects.filter(
                uuid__in=attachment_uuid_values,
                owner=user,
                status=UploadedMedia.Status.UPLOADED,
            )
            media_map = {str(media.uuid): media for media in media_queryset}
            ordered_media = []

            for attachment_uuid in attachment_uuid_values:
                media = media_map.get(str(attachment_uuid))
                if not media:
                    raise serializers.ValidationError(
                        {"attachment_uuids": f"Uploaded media not found or not ready: {attachment_uuid}"}
                    )
                ordered_media.append(media)

            uploaded_media = ordered_media

        if message_type == Message.MessageType.IMAGE:
            if len(uploaded_media) == 0:
                raise serializers.ValidationError({"attachment_uuids": "Image message requires attachments"})
            if len(uploaded_media) > 10:
                raise serializers.ValidationError({"attachment_uuids": "Only up to 10 images per message"})
            if any(media.media_kind != UploadedMedia.MediaKind.IMAGE for media in uploaded_media):
                raise serializers.ValidationError({"attachment_uuids": "Image message accepts only image attachments"})

        if message_type == Message.MessageType.VIDEO:
            if len(uploaded_media) != 1:
                raise serializers.ValidationError({"attachment_uuids": "Video message requires exactly one video"})
            media = uploaded_media[0]
            if media.media_kind != UploadedMedia.MediaKind.VIDEO:
                raise serializers.ValidationError({"attachment_uuids": "Attachment must be video"})
            duration = int((media.meta or {}).get("duration_seconds") or 0)
            if duration <= 0:
                raise serializers.ValidationError({"attachment_uuids": "Video duration_seconds is required"})
            if duration > VIDEO_MAX_DURATION_SECONDS:
                raise serializers.ValidationError(
                    {"attachment_uuids": f"Video duration must be <= {VIDEO_MAX_DURATION_SECONDS}s"}
                )

        if message_type == Message.MessageType.AUDIO:
            if len(uploaded_media) != 1:
                raise serializers.ValidationError({"attachment_uuids": "Voice message requires exactly one audio"})
            media = uploaded_media[0]
            if media.media_kind != UploadedMedia.MediaKind.AUDIO:
                raise serializers.ValidationError({"attachment_uuids": "Attachment must be audio"})
            duration = int((media.meta or {}).get("duration_seconds") or 0)
            if duration <= 0:
                raise serializers.ValidationError({"attachment_uuids": "Audio duration_seconds is required"})
            if duration > AUDIO_MAX_DURATION_SECONDS:
                raise serializers.ValidationError(
                    {"attachment_uuids": f"Audio duration must be <= {AUDIO_MAX_DURATION_SECONDS}s"}
                )

        if not text and not uploaded_media and message_type == Message.MessageType.TEXT:
            raise serializers.ValidationError({"text": "Text is required for text messages without attachments"})

        attrs["text"] = text
        attrs["uploaded_media"] = uploaded_media
        return attrs

    def create(self, validated_data):
        chat = self.context["chat"]
        sender = self.context["request"].user
        client_uuid = validated_data.get("client_uuid")

        if client_uuid:
            existing = Message.objects.filter(client_uuid=client_uuid).first()
            if existing:
                self.was_existing = True
                return existing

        message = Message.objects.create(
            chat=chat,
            sender=sender,
            client_uuid=client_uuid,
            message_type=validated_data.get("message_type", Message.MessageType.TEXT),
            text=validated_data.get("text", ""),
            reply_to=validated_data.get("reply_to"),
            metadata=validated_data.get("metadata", {}),
        )

        uploaded_media = validated_data.get("uploaded_media", [])
        if uploaded_media:
            MessageAttachment.objects.bulk_create(
                [
                    MessageAttachment(
                        message=message,
                        media=media,
                        sort_order=index,
                    )
                    for index, media in enumerate(uploaded_media)
                ],
                ignore_conflicts=True,
            )

        recipient_ids = list(
            chat.members.filter(is_active=True)
            .exclude(user_id=sender.id)
            .values_list("user_id", flat=True)
        )

        if recipient_ids:
            MessageReceipt.objects.bulk_create(
                [
                    MessageReceipt(
                        message=message,
                        user_id=user_id,
                    )
                    for user_id in recipient_ids
                ],
                ignore_conflicts=True,
            )

        chat.last_message_at = message.created_at
        chat.save(update_fields=["last_message_at", "updated_at"])

        self.was_existing = False
        return message


class MessageUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        message = self.context["message"]

        if message.sender_id != request.user.id:
            raise serializers.ValidationError("Only the sender can edit this message")

        if message.is_deleted:
            raise serializers.ValidationError("Deleted messages cannot be edited")

        if "text" not in attrs and "metadata" not in attrs:
            raise serializers.ValidationError("Nothing to update")

        normalized_text = (attrs.get("text", message.text) or "").strip()

        if message.message_type == Message.MessageType.TEXT and not normalized_text:
            raise serializers.ValidationError({"text": "Text cannot be empty for text messages"})

        attrs["normalized_text"] = normalized_text
        return attrs

    def save(self, **kwargs):
        message = self.context["message"]
        changed = []

        if "text" in self.validated_data and message.text != self.validated_data["normalized_text"]:
            message.text = self.validated_data["normalized_text"]
            changed.append("text")

        if "metadata" in self.validated_data and message.metadata != self.validated_data["metadata"]:
            message.metadata = self.validated_data["metadata"] or {}
            changed.append("metadata")

        if changed:
            message.is_edited = True
            message.edited_at = timezone.now()
            changed.extend(["is_edited", "edited_at", "updated_at"])
            message.save(update_fields=changed)

        return message


class MessageDeleteSerializer(serializers.Serializer):
    DELETE_FOR_ME = "me"
    DELETE_FOR_EVERYONE = "everyone"

    delete_for = serializers.ChoiceField(
        choices=[
            (DELETE_FOR_ME, "Delete only for me"),
            (DELETE_FOR_EVERYONE, "Delete for everyone"),
        ],
        default=DELETE_FOR_ME,
    )

    def validate(self, attrs):
        request = self.context["request"]
        message = self.context["message"]
        delete_for = attrs["delete_for"]

        if delete_for == self.DELETE_FOR_EVERYONE and message.sender_id != request.user.id:
            raise serializers.ValidationError("Only the sender can delete this message for everyone")

        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        message = self.context["message"]
        delete_for = self.validated_data["delete_for"]
        now = timezone.now()

        if delete_for == self.DELETE_FOR_ME:
            state, created = MessageUserState.objects.get_or_create(
                message=message,
                user=request.user,
                defaults={
                    "is_hidden": True,
                    "hidden_at": now,
                },
            )

            if not created:
                state.is_hidden = True
                state.hidden_at = now
                state.save(update_fields=["is_hidden", "hidden_at", "updated_at"])

            return {
                "delete_for": delete_for,
                "message": message,
            }

        if not message.is_deleted:
            message.is_deleted = True
            message.deleted_at = now
            message.text = ""
            message.metadata = {}
            message.save(
                update_fields=[
                    "is_deleted",
                    "deleted_at",
                    "text",
                    "metadata",
                    "updated_at",
                ]
            )

        return {
            "delete_for": delete_for,
            "message": message,
        }
