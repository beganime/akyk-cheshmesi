from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import ChatMember
from apps.chats.utils import get_or_create_direct_chat_between
from apps.messaging.models import Message
from apps.messaging.realtime_events import publish_realtime_event
from apps.messaging.serializers import MessageCreateSerializer, MessageListSerializer

from .models import Story, StoryView
from .serializers import (
    StoryCreateSerializer,
    StoryReactionSerializer,
    StoryReplySerializer,
    StorySerializer,
    StoryViewSerializer,
)


def visible_story_queryset(user):
    shared_chat_user_ids = ChatMember.objects.filter(
        chat__members__user=user,
        chat__members__is_active=True,
        chat__is_active=True,
        is_active=True,
    ).values_list("user_id", flat=True)

    return (
        Story.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        .filter(Q(author=user) | Q(author_id__in=shared_chat_user_ids))
        .select_related("author", "media")
        .annotate(views_count_value=Count("views", distinct=True))
        .distinct()
    )


class StoryListCreateAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "stories"

    def get_throttles(self):
        self.throttle_scope = "stories_create" if self.request.method == "POST" else "stories"
        return super().get_throttles()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoryCreateSerializer
        return StorySerializer

    def get(self, request):
        queryset = visible_story_queryset(request.user).order_by("author_id", "-created_at")
        serializer = StorySerializer(queryset, many=True, context={"request": request})
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StoryCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        story = serializer.save()
        output = StorySerializer(story, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class StoryDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StorySerializer
    lookup_url_kwarg = "story_uuid"

    def get_story(self):
        return get_object_or_404(visible_story_queryset(self.request.user), uuid=self.kwargs["story_uuid"])

    def get(self, request, *args, **kwargs):
        story = self.get_story()
        if story.author_id != request.user.id:
            StoryView.objects.update_or_create(
                story=story,
                viewer=request.user,
                defaults={"viewed_at": timezone.now()},
            )
        serializer = self.get_serializer(story, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        story = get_object_or_404(Story, uuid=self.kwargs["story_uuid"], author=request.user)
        story.is_active = False
        story.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class StoryViewersAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_story(self):
        return get_object_or_404(visible_story_queryset(self.request.user), uuid=self.kwargs["story_uuid"])

    def get(self, request, story_uuid):
        story = get_object_or_404(Story, uuid=story_uuid, author=request.user)
        viewers = story.views.select_related("viewer").order_by("-viewed_at")
        serializer = StoryViewSerializer(viewers, many=True, context={"request": request})
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, story_uuid):
        story = self.get_story()
        if story.author_id != request.user.id:
            StoryView.objects.update_or_create(
                story=story,
                viewer=request.user,
                defaults={"viewed_at": timezone.now()},
            )
        serializer = StorySerializer(story, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


def _mark_story_viewed(story, user):
    if story.author_id != user.id:
        StoryView.objects.update_or_create(
            story=story,
            viewer=user,
            defaults={"viewed_at": timezone.now()},
        )


def _publish_story_message(message, request):
    message = (
        Message.objects.select_related("sender", "reply_to", "reply_to__sender")
        .prefetch_related("receipts", "attachments__media")
        .get(id=message.id)
    )
    output_data = MessageListSerializer(message, context={"request": request}).data
    payload = {
        "message": output_data,
        "message_uuid": str(message.uuid),
        "chat_uuid": str(message.chat.uuid),
        "sender_uuid": str(message.sender.uuid),
        "client_uuid": str(message.client_uuid or ""),
        "message_type": message.message_type,
    }
    publish_realtime_event("message_persisted", str(message.chat.uuid), {**payload, "persisted_status": "saved"})
    publish_realtime_event("message:new", str(message.chat.uuid), payload)
    return output_data


class BaseStoryInteractionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None
    story_action = ""

    def get_story(self):
        return get_object_or_404(visible_story_queryset(self.request.user), uuid=self.kwargs["story_uuid"])

    def build_message_text(self, serializer):
        raise NotImplementedError

    def build_metadata(self, story, serializer):
        return {
            "story_uuid": str(story.uuid),
            "story_author_uuid": str(story.author.uuid),
            "story_action": self.story_action,
            "story_media_type": story.media_type,
            "story_caption": story.caption,
        }

    def post(self, request, story_uuid):
        story = self.get_story()
        if story.author_id == request.user.id:
            return Response({"detail": "You cannot reply/react to your own story"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat = get_or_create_direct_chat_between(request.user, story.author)
        message_serializer = MessageCreateSerializer(
            data={
                "message_type": "text",
                "text": self.build_message_text(serializer),
                "metadata": self.build_metadata(story, serializer),
            },
            context={"request": request, "chat": chat},
        )
        message_serializer.is_valid(raise_exception=True)
        message = message_serializer.save()
        _mark_story_viewed(story, request.user)
        message_data = _publish_story_message(message, request)

        return Response(
            {
                "detail": f"Story {self.story_action} sent",
                "story_uuid": str(story.uuid),
                "chat_uuid": str(chat.uuid),
                "message": message_data,
            },
            status=status.HTTP_201_CREATED,
        )


class StoryReplyAPIView(BaseStoryInteractionAPIView):
    serializer_class = StoryReplySerializer
    story_action = "reply"

    def build_message_text(self, serializer):
        return serializer.validated_data["text"]


class StoryReactionAPIView(BaseStoryInteractionAPIView):
    serializer_class = StoryReactionSerializer
    story_action = "reaction"

    def build_message_text(self, serializer):
        return serializer.validated_data["emoji"]

    def build_metadata(self, story, serializer):
        metadata = super().build_metadata(story, serializer)
        metadata["reaction"] = serializer.validated_data["emoji"]
        return metadata
