from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.chats.models import Chat
from apps.messaging.models import Message

from .models import Complaint

User = get_user_model()


class ComplaintSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True)

    class Meta:
        model = Complaint
        fields = (
            "uuid",
            "complaint_type",
            "reason",
            "description",
            "status",
            "reporter_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("uuid", "status", "reporter_email", "created_at", "updated_at")


class ComplaintCreateSerializer(serializers.Serializer):
    complaint_type = serializers.ChoiceField(choices=Complaint.ComplaintType.choices)
    reason = serializers.ChoiceField(choices=Complaint.Reason.choices)
    description = serializers.CharField(required=False, allow_blank=True)
    reported_user_uuid = serializers.UUIDField(required=False)
    chat_uuid = serializers.UUIDField(required=False)
    message_uuid = serializers.UUIDField(required=False)

    def validate(self, attrs):
        complaint_type = attrs["complaint_type"]
        request = self.context["request"]

        reported_user_uuid = attrs.get("reported_user_uuid")
        chat_uuid = attrs.get("chat_uuid")
        message_uuid = attrs.get("message_uuid")

        filled = sum(bool(value) for value in [reported_user_uuid, chat_uuid, message_uuid])

        if complaint_type == Complaint.ComplaintType.APP:
            if filled:
                raise serializers.ValidationError("App complaint must not contain target user/chat/message")
            return attrs

        if filled != 1:
            raise serializers.ValidationError(
                "Exactly one target must be provided: reported_user_uuid, chat_uuid or message_uuid"
            )

        if complaint_type == Complaint.ComplaintType.USER:
            user = User.objects.filter(uuid=reported_user_uuid, is_active=True).first()
            if not user:
                raise serializers.ValidationError({"reported_user_uuid": "User not found"})
            if user.id == request.user.id:
                raise serializers.ValidationError({"reported_user_uuid": "You cannot complain about yourself"})
            attrs["reported_user"] = user

        elif complaint_type == Complaint.ComplaintType.CHAT:
            chat = Chat.objects.filter(uuid=chat_uuid, is_active=True).first()
            if not chat:
                raise serializers.ValidationError({"chat_uuid": "Chat not found"})
            attrs["chat"] = chat

        elif complaint_type == Complaint.ComplaintType.MESSAGE:
            message = Message.objects.filter(uuid=message_uuid).select_related("chat", "sender").first()
            if not message:
                raise serializers.ValidationError({"message_uuid": "Message not found"})
            if message.sender_id == request.user.id:
                raise serializers.ValidationError({"message_uuid": "You cannot complain about your own message"})
            attrs["message"] = message
            attrs["chat"] = message.chat
            attrs["reported_user"] = message.sender

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        return Complaint.objects.create(
            reporter=request.user,
            complaint_type=validated_data["complaint_type"],
            reason=validated_data["reason"],
            description=validated_data.get("description", "").strip(),
            reported_user=validated_data.get("reported_user"),
            chat=validated_data.get("chat"),
            message=validated_data.get("message"),
        )