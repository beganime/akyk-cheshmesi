from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.chats.models import Chat, ChatMember
from apps.users.public_serializers import UserShortSerializer

from .models import CallEvent, CallParticipant, CallSession
from .services import ACTIVE_CALL_STATUSES, create_call_event


class CallParticipantSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = CallParticipant
        fields = (
            "uuid",
            "role",
            "status",
            "invited_at",
            "joined_at",
            "left_at",
            "duration_seconds",
            "device_id",
            "device_platform",
            "device_name",
            "is_muted",
            "is_video_enabled",
            "metadata",
            "user",
        )


class CallEventSerializer(serializers.ModelSerializer):
    actor = UserShortSerializer(read_only=True)

    class Meta:
        model = CallEvent
        fields = (
            "uuid",
            "event_type",
            "payload",
            "created_at",
            "actor",
        )


class CallSessionListSerializer(serializers.ModelSerializer):
    initiated_by = UserShortSerializer(read_only=True)
    participants = CallParticipantSerializer(many=True, read_only=True)
    chat_uuid = serializers.UUIDField(source="chat.uuid", read_only=True)
    my_status = serializers.SerializerMethodField()

    class Meta:
        model = CallSession
        fields = (
            "uuid",
            "chat_uuid",
            "call_type",
            "status",
            "room_key",
            "answered_at",
            "ended_at",
            "duration_seconds",
            "metadata",
            "created_at",
            "initiated_by",
            "participants",
            "my_status",
        )

    def get_my_status(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        participant = next(
            (item for item in obj.participants.all() if item.user_id == request.user.id),
            None,
        )
        return participant.status if participant else None


class CallSessionDetailSerializer(CallSessionListSerializer):
    events = CallEventSerializer(many=True, read_only=True)

    class Meta(CallSessionListSerializer.Meta):
        fields = CallSessionListSerializer.Meta.fields + ("events",)


class CallCreateSerializer(serializers.Serializer):
    call_type = serializers.ChoiceField(choices=CallSession.CallType.choices)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        chat: Chat = self.context["chat"]

        membership = ChatMember.objects.filter(
            chat=chat,
            user=request.user,
            is_active=True,
        ).first()
        if not membership:
            raise serializers.ValidationError("You are not a member of this chat")

        active_call_exists = CallSession.objects.filter(
            chat=chat,
            status__in=ACTIVE_CALL_STATUSES,
        ).exists()
        if active_call_exists:
            raise serializers.ValidationError("There is already an active call in this chat")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        chat: Chat = self.context["chat"]
        metadata = validated_data.get("metadata", {}) or {}
        now = timezone.now()

        members = list(
            ChatMember.objects.filter(
                chat=chat,
                is_active=True,
            ).select_related("user")
        )

        with transaction.atomic():
            session = CallSession.objects.create(
                chat=chat,
                initiated_by=request.user,
                call_type=validated_data["call_type"],
                status=CallSession.Status.RINGING,
                metadata=metadata,
            )

            participant_rows = []
            for member in members:
                if member.user_id == request.user.id:
                    participant_rows.append(
                        CallParticipant(
                            session=session,
                            user=member.user,
                            role=CallParticipant.Role.CALLER,
                            status=CallParticipant.Status.JOINED,
                            joined_at=now,
                            device_id=str(metadata.get("device_id", ""))[:128],
                            device_platform=str(metadata.get("device_platform", ""))[:32],
                            device_name=str(metadata.get("device_name", ""))[:128],
                            metadata=metadata,
                        )
                    )
                else:
                    participant_rows.append(
                        CallParticipant(
                            session=session,
                            user=member.user,
                            role=(
                                CallParticipant.Role.CALLEE
                                if chat.chat_type == Chat.ChatType.DIRECT
                                else CallParticipant.Role.PARTICIPANT
                            ),
                            status=CallParticipant.Status.RINGING,
                            metadata={},
                        )
                    )

            CallParticipant.objects.bulk_create(participant_rows)

            create_call_event(
                session=session,
                event_type="call_invite",
                actor=request.user,
                payload={
                    "initiated_by_uuid": str(request.user.uuid),
                    "initiated_by_username": request.user.username or "",
                    "call_type": session.call_type,
                },
                publish=True,
            )

        return session


class CallActionSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=128)
    device_platform = serializers.CharField(required=False, allow_blank=True, max_length=32)
    device_name = serializers.CharField(required=False, allow_blank=True, max_length=128)