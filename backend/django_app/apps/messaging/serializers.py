from rest_framework import serializers

from apps.mediafiles.models import MessageAttachment, UploadedMedia
from apps.mediafiles.serializers import MediaAttachmentBriefSerializer
from apps.messaging.models import Message, MessageReceipt
from apps.users.public_serializers import UserShortSerializer


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
        media_items = [attachment.media for attachment in self._get_attachments(obj)]
        return MediaAttachmentBriefSerializer(media_items, many=True).data


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

        if not text and not uploaded_media and message_type == Message.MessageType.TEXT:
            raise serializers.ValidationError(
                {"text": "Text is required for text messages without attachments"}
            )

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