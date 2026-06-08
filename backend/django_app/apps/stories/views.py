from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import ChatMember

from .models import Story, StoryView
from .serializers import StoryCreateSerializer, StorySerializer, StoryViewSerializer


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
