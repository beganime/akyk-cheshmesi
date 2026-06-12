import re
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.bots.models import BotMembership, BotProfile, default_bot_scopes
from apps.chats.models import Chat, ChatMember
from apps.messaging.models import Message
from apps.messaging.serializers import MessageCreateSerializer
from apps.users.public_serializers import UserShortSerializer

User = get_user_model()

BOT_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,31}$")
ALLOWED_SCOPES = {"send_message", "read_messages", "upload_media", "manage_chat"}


def generate_bot_token() -> str:
    return f"bot_{secrets.token_urlsafe(32)}"


def normalize_scopes(scopes) -> list[str]:
    if not scopes:
        return default_bot_scopes()
    if not isinstance(scopes, list):
        raise serializers.ValidationError("Scopes must be a list")
    normalized = []
    for scope in scopes:
        value = str(scope).strip()
        if value not in ALLOWED_SCOPES:
            raise serializers.ValidationError(f"Unsupported bot scope: {value}")
        if value not in normalized:
            normalized.append(value)
    return normalized or default_bot_scopes()


class BotCommandResolveSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=120)


class BotCommandResponseSerializer(serializers.Serializer):
    command = serializers.CharField()
    response_text = serializers.CharField()


class BotProfileSerializer(serializers.ModelSerializer):
    owner = UserShortSerializer(read_only=True)
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = BotProfile
        fields = (
            "uuid",
            "code",
            "username",
            "title",
            "description",
            "avatar",
            "scopes",
            "webhook_url",
            "is_active",
            "last_used_at",
            "token_last_rotated_at",
            "owner",
            "user",
            "created_at",
            "updated_at",
        )


class BotCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=32)
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
    scopes = serializers.JSONField(required=False)
    webhook_url = serializers.URLField(required=False, allow_blank=True)

    def validate_username(self, value):
        username = value.strip().lstrip("@")
        if not BOT_USERNAME_RE.match(username):
            raise serializers.ValidationError("Use 3-32 letters, numbers or underscores; start with a letter")
        if BotProfile.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Bot username already exists")
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Username is already used by a user")
        return username

    def validate_scopes(self, value):
        return normalize_scopes(value)

    def create(self, validated_data):
        owner = self.context["request"].user
        username = validated_data["username"]
        token = generate_bot_token()

        with transaction.atomic():
            bot_user = User.objects.create_user(
                email=f"{username}@bots.akyl.local",
                username=username,
                password=None,
                first_name=validated_data["title"].strip(),
                is_active=True,
                is_email_verified=True,
                registration_completed=True,
            )
            bot = BotProfile.objects.create(
                owner=owner,
                user=bot_user,
                code=username,
                username=username,
                title=validated_data["title"].strip(),
                description=(validated_data.get("description") or "").strip(),
                avatar=validated_data.get("avatar"),
                scopes=validated_data.get("scopes") or default_bot_scopes(),
                webhook_url=(validated_data.get("webhook_url") or "").strip(),
                token_hash=make_password(token),
                token_last_rotated_at=timezone.now(),
                is_active=True,
            )

        self.generated_token = token
        return bot


class BotUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=120)
    description = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
    scopes = serializers.JSONField(required=False)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate_scopes(self, value):
        return normalize_scopes(value)

    def update(self, instance, validated_data):
        changed = []
        for field in ("title", "description", "avatar", "scopes", "webhook_url", "is_active"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                changed.append(field)
        if changed:
            changed.append("updated_at")
            instance.save(update_fields=changed)
        return instance


class BotMembershipSerializer(serializers.ModelSerializer):
    bot = BotProfileSerializer(read_only=True)

    class Meta:
        model = BotMembership
        fields = ("uuid", "bot", "scopes", "is_active", "created_at", "updated_at")


class BotAddToChatSerializer(serializers.Serializer):
    bot_uuid = serializers.UUIDField()
    scopes = serializers.JSONField(required=False)

    def validate_scopes(self, value):
        return normalize_scopes(value)

    def validate_bot_uuid(self, value):
        request = self.context["request"]
        bot = BotProfile.objects.filter(uuid=value, owner=request.user, is_active=True).first()
        if not bot:
            raise serializers.ValidationError("Bot not found")
        self.bot = bot
        return value

    def save(self, **kwargs):
        chat = self.context["chat"]
        request = self.context["request"]
        membership, _ = BotMembership.objects.update_or_create(
            bot=self.bot,
            chat=chat,
            defaults={
                "added_by": request.user,
                "scopes": self.validated_data.get("scopes") or self.bot.scopes or default_bot_scopes(),
                "is_active": True,
            },
        )
        if self.bot.user_id:
            ChatMember.objects.update_or_create(
                chat=chat,
                user=self.bot.user,
                defaults={
                    "role": ChatMember.Role.MEMBER,
                    "is_active": True,
                    "can_send_messages": True,
                },
            )
            chat.members_count = chat.members.filter(is_active=True).count()
            chat.save(update_fields=["members_count", "updated_at"])
        return membership


class BotSendMessageSerializer(serializers.Serializer):
    chat_uuid = serializers.UUIDField()
    text = serializers.CharField(required=False, allow_blank=True)
    message_type = serializers.ChoiceField(choices=[("text", "Text")], default="text")
    client_uuid = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        bot = self.context["bot"]
        chat = Chat.objects.filter(uuid=attrs["chat_uuid"], is_active=True).first()
        if not chat:
            raise serializers.ValidationError({"chat_uuid": "Chat not found"})

        membership = BotMembership.objects.filter(bot=bot, chat=chat, is_active=True).first()
        if not membership:
            raise serializers.ValidationError("Bot is not a member of this chat")
        if "send_message" not in (membership.scopes or []):
            raise serializers.ValidationError("Bot is not allowed to send messages")
        if not (attrs.get("text") or "").strip():
            raise serializers.ValidationError({"text": "Text is required"})

        attrs["chat"] = chat
        attrs["membership"] = membership
        attrs["text"] = attrs["text"].strip()
        return attrs

    def create(self, validated_data):
        bot = self.context["bot"]
        fake_request = type("BotRequest", (), {"user": bot.user})()
        metadata = {
            **(validated_data.get("metadata") or {}),
            "bot_uuid": str(bot.uuid),
            "bot_username": bot.username or bot.code,
            "bot_title": bot.title,
        }
        message_payload = {
            "message_type": Message.MessageType.TEXT,
            "text": validated_data["text"],
            "metadata": metadata,
        }
        if validated_data.get("client_uuid"):
            message_payload["client_uuid"] = validated_data["client_uuid"]

        serializer = MessageCreateSerializer(
            data=message_payload,
            context={"request": fake_request, "chat": validated_data["chat"], "allow_bot": True},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        bot.last_used_at = timezone.now()
        bot.save(update_fields=["last_used_at", "updated_at"])
        return message


def authenticate_bot_token(raw_header: str | None) -> BotProfile | None:
    value = (raw_header or "").strip()
    if value.lower().startswith("bot "):
        token = value[4:].strip()
    else:
        token = value
    if not token:
        return None

    for bot in BotProfile.objects.filter(is_active=True).exclude(token_hash="").select_related("user"):
        if check_password(token, bot.token_hash):
            return bot
    return None
