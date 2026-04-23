from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import Chat

from .models import CallParticipant, CallSession
from .serializers import (
    CallActionSerializer,
    CallCreateSerializer,
    CallSessionDetailSerializer,
    CallSessionListSerializer,
)
from .services import create_call_event, finalize_call_session, finalize_participant_if_joined


def call_queryset_for_user(user):
    return (
        CallSession.objects.filter(participants__user=user)
        .select_related("chat", "initiated_by")
        .prefetch_related(
            Prefetch(
                "participants",
                queryset=CallParticipant.objects.select_related("user").order_by("created_at"),
            ),
            "events__actor",
        )
        .distinct()
        .order_by("-created_at")
    )


class CallHistoryListAPIView(generics.ListAPIView):
    serializer_class = CallSessionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = call_queryset_for_user(self.request.user)
        chat_uuid = self.request.query_params.get("chat_uuid")
        status_value = self.request.query_params.get("status")

        if chat_uuid:
            queryset = queryset.filter(chat__uuid=chat_uuid)
        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset


class CallDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CallSessionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "call_uuid"

    def get_queryset(self):
        return call_queryset_for_user(self.request.user)


class ChatCallCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_uuid):
        chat = get_object_or_404(Chat, uuid=chat_uuid, is_active=True)
        serializer = CallCreateSerializer(
            data=request.data,
            context={"request": request, "chat": chat},
        )
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        output = CallSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class BaseCallActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_session(self, request, call_uuid) -> CallSession:
        return get_object_or_404(
            CallSession.objects.select_related("chat", "initiated_by")
            .prefetch_related("participants__user"),
            uuid=call_uuid,
            participants__user=request.user,
        )

    def get_participant(self, session: CallSession, user):
        return get_object_or_404(
            CallParticipant,
            session=session,
            user=user,
        )


class CallAcceptAPIView(BaseCallActionAPIView):
    def post(self, request, call_uuid):
        serializer = CallActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            session = self.get_session(request, call_uuid)
            participant = self.get_participant(session, request.user)

            if session.status not in {
                CallSession.Status.REQUESTED,
                CallSession.Status.RINGING,
                CallSession.Status.ACCEPTED,
            }:
                return Response(
                    {"detail": "This call cannot be accepted anymore"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if participant.status == CallParticipant.Status.JOINED:
                output = CallSessionDetailSerializer(session, context={"request": request})
                return Response(output.data, status=status.HTTP_200_OK)

            if participant.status not in {
                CallParticipant.Status.INVITED,
                CallParticipant.Status.RINGING,
            }:
                return Response(
                    {"detail": "Your participation state does not allow accept"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()
            participant.status = CallParticipant.Status.JOINED
            participant.joined_at = now
            participant.device_id = serializer.validated_data.get("device_id", participant.device_id)
            participant.device_platform = serializer.validated_data.get(
                "device_platform",
                participant.device_platform,
            )
            participant.device_name = serializer.validated_data.get("device_name", participant.device_name)
            participant.metadata = serializer.validated_data.get("metadata", participant.metadata or {})
            participant.save(
                update_fields=[
                    "status",
                    "joined_at",
                    "device_id",
                    "device_platform",
                    "device_name",
                    "metadata",
                    "updated_at",
                ]
            )

            if session.answered_at is None:
                session.answered_at = now
            session.status = CallSession.Status.ACCEPTED
            session.save(update_fields=["answered_at", "status", "updated_at"])

            create_call_event(
                session=session,
                event_type="call_accepted",
                actor=request.user,
                payload={
                    "user_uuid": str(request.user.uuid),
                    "username": request.user.username or "",
                },
                publish=True,
            )

        output = CallSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class CallRejectAPIView(BaseCallActionAPIView):
    def post(self, request, call_uuid):
        serializer = CallActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            session = self.get_session(request, call_uuid)
            participant = self.get_participant(session, request.user)

            if session.status not in {
                CallSession.Status.REQUESTED,
                CallSession.Status.RINGING,
                CallSession.Status.ACCEPTED,
            }:
                return Response(
                    {"detail": "This call cannot be rejected anymore"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if participant.status == CallParticipant.Status.JOINED:
                return Response(
                    {"detail": "Joined participant must end the call instead of reject"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            participant.status = CallParticipant.Status.DECLINED
            participant.left_at = timezone.now()
            participant.metadata = serializer.validated_data.get("metadata", participant.metadata or {})
            participant.save(update_fields=["status", "left_at", "metadata", "updated_at"])

            other_joined_exists = session.participants.exclude(user=request.user).filter(
                status=CallParticipant.Status.JOINED
            ).exists()
            other_ringing_exists = session.participants.exclude(user=request.user).filter(
                status__in=[CallParticipant.Status.INVITED, CallParticipant.Status.RINGING]
            ).exists()

            if not other_joined_exists and not other_ringing_exists:
                session = finalize_call_session(session, CallSession.Status.REJECTED)

            create_call_event(
                session=session,
                event_type="call_rejected",
                actor=request.user,
                payload={
                    "user_uuid": str(request.user.uuid),
                    "username": request.user.username or "",
                },
                publish=True,
            )

        output = CallSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class CallCancelAPIView(BaseCallActionAPIView):
    def post(self, request, call_uuid):
        serializer = CallActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            session = self.get_session(request, call_uuid)

            if session.initiated_by_id != request.user.id:
                return Response(
                    {"detail": "Only call initiator can cancel the call"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if session.status not in {
                CallSession.Status.REQUESTED,
                CallSession.Status.RINGING,
            }:
                return Response(
                    {"detail": "Only pending/ringing call can be canceled"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session = finalize_call_session(session, CallSession.Status.CANCELED)

            for participant in session.participants.all():
                if participant.status in {
                    CallParticipant.Status.INVITED,
                    CallParticipant.Status.RINGING,
                }:
                    participant.status = CallParticipant.Status.MISSED
                    participant.left_at = timezone.now()
                    participant.save(update_fields=["status", "left_at", "updated_at"])
                elif participant.status == CallParticipant.Status.JOINED:
                    finalize_participant_if_joined(participant)

            create_call_event(
                session=session,
                event_type="call_canceled",
                actor=request.user,
                payload={
                    "user_uuid": str(request.user.uuid),
                    "username": request.user.username or "",
                },
                publish=True,
            )

        output = CallSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class CallEndAPIView(BaseCallActionAPIView):
    def post(self, request, call_uuid):
        serializer = CallActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            session = self.get_session(request, call_uuid)
            participant = self.get_participant(session, request.user)

            if session.status not in {
                CallSession.Status.ACCEPTED,
                CallSession.Status.RINGING,
            }:
                return Response(
                    {"detail": "This call is already finished"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if participant.status == CallParticipant.Status.JOINED:
                finalize_participant_if_joined(participant)
            elif participant.status in {
                CallParticipant.Status.INVITED,
                CallParticipant.Status.RINGING,
            }:
                participant.status = CallParticipant.Status.MISSED
                participant.left_at = timezone.now()
                participant.save(update_fields=["status", "left_at", "updated_at"])

            active_joined_exists = session.participants.filter(
                status=CallParticipant.Status.JOINED
            ).exists()
            active_ringing_exists = session.participants.filter(
                status__in=[CallParticipant.Status.INVITED, CallParticipant.Status.RINGING]
            ).exists()

            if not active_joined_exists and not active_ringing_exists:
                session = finalize_call_session(session, CallSession.Status.ENDED)
            elif not active_joined_exists and active_ringing_exists:
                session = finalize_call_session(session, CallSession.Status.MISSED)

            create_call_event(
                session=session,
                event_type="call_ended",
                actor=request.user,
                payload={
                    "user_uuid": str(request.user.uuid),
                    "username": request.user.username or "",
                },
                publish=True,
            )

        output = CallSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)