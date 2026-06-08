from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.mediafiles.models import UploadedMedia
from apps.mediafiles.serializers import UploadedMediaSerializer
from apps.users.public_serializers import UserShortSerializer

from .models import Story, StoryView


class StoryViewSerializer(serializers.ModelSerializer):
    viewer = UserShortSerializer(read_only=True)

    class Meta:
        model = StoryView
        fields = ("uuid", "viewer", "viewed_at")


class StorySerializer(serializers.ModelSerializer):
    author = UserShortSerializer(read_only=True)
    media = UploadedMediaSerializer(read_only=True)
    viewed_by_me = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = (
            "uuid",
            "author",
            "media",
            "media_type",
            "caption",
            "background",
            "expires_at",
            "is_active",
            "metadata",
            "viewed_by_me",
            "views_count",
            "created_at",
            "updated_at",
        )

    def get_viewed_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.author_id == request.user.id:
            return True
        return obj.views.filter(viewer=request.user).exists()

    def get_views_count(self, obj):
        request = self.context.get("request")
        if not request or obj.author_id != request.user.id:
            return None
        annotated = getattr(obj, "views_count_value", None)
        if annotated is not None:
            return int(annotated)
        return obj.views.count()


class StoryCreateSerializer(serializers.Serializer):
    media_type = serializers.ChoiceField(choices=Story.MediaType.choices)
    media_uuid = serializers.UUIDField(required=False)
    caption = serializers.CharField(required=False, allow_blank=True)
    background = serializers.CharField(required=False, allow_blank=True, max_length=64)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        media_type = attrs["media_type"]
        media_uuid = attrs.get("media_uuid")
        caption = (attrs.get("caption") or "").strip()
        background = (attrs.get("background") or "").strip()

        media = None
        if media_uuid:
            media = UploadedMedia.objects.filter(
                uuid=media_uuid,
                owner=request.user,
                status=UploadedMedia.Status.UPLOADED,
            ).first()
            if not media:
                raise serializers.ValidationError({"media_uuid": "Media not found or not ready"})

        if media_type in {Story.MediaType.IMAGE, Story.MediaType.VIDEO}:
            if not media:
                raise serializers.ValidationError({"media_uuid": "Media story requires uploaded media"})
            expected_kind = UploadedMedia.MediaKind.IMAGE if media_type == Story.MediaType.IMAGE else UploadedMedia.MediaKind.VIDEO
            if media.media_kind != expected_kind:
                raise serializers.ValidationError({"media_uuid": f"Story media must be {expected_kind}"})

        if media_type == Story.MediaType.TEXT:
            if media:
                raise serializers.ValidationError({"media_uuid": "Text story cannot include media"})
            if not caption:
                raise serializers.ValidationError({"caption": "Text story requires caption"})

        attrs["media"] = media
        attrs["caption"] = caption
        attrs["background"] = background
        return attrs

    def create(self, validated_data):
        ttl_hours = getattr(settings, "STORY_TTL_HOURS", 24)
        return Story.objects.create(
            author=self.context["request"].user,
            media=validated_data.get("media"),
            media_type=validated_data["media_type"],
            caption=validated_data.get("caption", ""),
            background=validated_data.get("background", ""),
            metadata=validated_data.get("metadata", {}) or {},
            expires_at=timezone.now() + timedelta(hours=ttl_hours),
            is_active=True,
        )
