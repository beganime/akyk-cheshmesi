import secrets
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import Chat, ChatMember
from apps.mediafiles.models import MessageAttachment, UploadedMedia
from apps.mediafiles.serializers import get_uploaded_media_file_url
from apps.mediafiles.validators import validate_upload_input
from apps.messaging.models import Message, MessageReceipt

from .models import User


SUPPORT_USERNAME = "sl-support"
SUPPORT_EMAIL = "sl-support@akyl.internal"
SUPPORT_CHAT_PREFIX = "sl-support:"


def has_sl_service_access(request):
    expected = str(getattr(settings, "MANAGER_SL_SERVICE_TOKEN", "") or "")
    supplied = str(request.headers.get("Authorization", "") or "")
    supplied = supplied[7:].strip() if supplied.startswith("Bearer ") else ""
    return bool(expected and supplied and secrets.compare_digest(expected, supplied))


def service_denied():
    return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)


def normalize_sl_id(value):
    sl_id = str(value or "").strip().upper()
    if not sl_id.startswith("SL-") or len(sl_id) > 32:
        raise ValueError("A valid SL-ID is required.")
    return sl_id


def split_name(full_name):
    parts = str(full_name or "").strip().split(maxsplit=1)
    return (parts[0] if parts else "Клиент", parts[1] if len(parts) > 1 else "")


def client_email(sl_id, requested=""):
    requested = str(requested or "").strip().casefold()
    if requested and not User.objects.filter(email__iexact=requested).exclude(username__iexact=sl_id).exists():
        return requested
    return f"{sl_id.casefold()}@clients.stud-life.internal"


def ensure_support_user():
    support, created = User.objects.get_or_create(
        username=SUPPORT_USERNAME,
        defaults={
            "email": SUPPORT_EMAIL,
            "first_name": "Менеджеры",
            "last_name": "Students Life",
            "is_active": True,
            "is_staff": True,
            "is_email_verified": True,
            "registration_completed": True,
        },
    )
    changed = []
    for field, value in {
        "email": SUPPORT_EMAIL,
        "is_active": True,
        "is_staff": True,
        "is_email_verified": True,
        "registration_completed": True,
    }.items():
        if getattr(support, field) != value:
            setattr(support, field, value)
            changed.append(field)
    if created or support.has_usable_password():
        support.set_unusable_password()
        changed.append("password")
    if changed:
        support.save(update_fields=[*dict.fromkeys(changed), "updated_at"])
    return support


def support_chat_for(sl_id):
    return Chat.objects.filter(direct_key=f"{SUPPORT_CHAT_PREFIX}{sl_id.casefold()}", is_active=True).first()


def provision_client(sl_id, full_name, password, email=""):
    first_name, last_name = split_name(full_name)
    support = ensure_support_user()
    with transaction.atomic():
        client = User.objects.select_for_update().filter(username__iexact=sl_id).first()
        created = client is None
        if client is None:
            client = User(username=sl_id, email=client_email(sl_id, email))
        client.first_name = first_name
        client.last_name = last_name
        client.is_active = True
        client.is_email_verified = True
        client.registration_completed = True
        client.set_password(password)
        client.save()

        chat, chat_created = Chat.objects.get_or_create(
            direct_key=f"{SUPPORT_CHAT_PREFIX}{sl_id.casefold()}",
            defaults={
                "chat_type": Chat.ChatType.GROUP,
                "title": f"{full_name} · {sl_id}",
                "description": "Консультация Students Life",
                "creator": support,
                "is_active": True,
            },
        )
        if not chat.is_active:
            chat.is_active = True
            chat.save(update_fields=["is_active", "updated_at"])

        ChatMember.objects.update_or_create(
            chat=chat,
            user=support,
            defaults={"role": ChatMember.Role.OWNER, "is_active": True, "can_send_messages": True},
        )
        ChatMember.objects.update_or_create(
            chat=chat,
            user=client,
            defaults={"role": ChatMember.Role.MEMBER, "is_active": True, "can_send_messages": True},
        )
        for manager in User.objects.filter(Q(is_staff=True) | Q(is_superuser=True), is_active=True).exclude(pk__in=[support.pk, client.pk]):
            ChatMember.objects.update_or_create(
                chat=chat,
                user=manager,
                defaults={"role": ChatMember.Role.ADMIN, "is_active": True, "can_send_messages": True},
            )
        chat.members_count = chat.members.filter(is_active=True).count()
        chat.save(update_fields=["members_count", "updated_at"])
    return client, chat, created, chat_created


def message_attachment_data(message, request):
    result = []
    for attachment in message.attachments.select_related("media"):
        media = attachment.media
        result.append(
            {
                "id": str(media.uuid),
                "url": get_uploaded_media_file_url(media, request=request),
                "original_name": media.original_name,
                "content_type": media.content_type,
                "size": media.size,
                "width": media.width,
                "height": media.height,
                "created_at": media.created_at,
            }
        )
    return result


def serialize_message(message, chat, client, actor, request):
    attachments = message_attachment_data(message, request)
    sender_is_manager = message.sender_id != client.id
    if sender_is_manager:
        sender_name = str((message.metadata or {}).get("manager_name") or "Менеджер Students Life")
    else:
        sender_name = message.sender.get_full_name() or message.sender.username or message.sender.email
    receipt_qs = message.receipts.exclude(user=message.sender)
    return {
        "id": str(message.uuid),
        "room": str(chat.uuid),
        "sender_user": str(message.sender.uuid),
        "sender_user_name": sender_name,
        "sender_staff": None,
        "sender_role": "manager" if sender_is_manager else "user",
        "sender_display_name": sender_name,
        "message_type": message.message_type,
        "text": message.text,
        "file": attachments[0]["url"] if attachments else None,
        "attachments": attachments,
        "is_mine": (actor == "manager" and sender_is_manager) or (actor == "client" and not sender_is_manager),
        "is_read": not receipt_qs.exists() or receipt_qs.filter(read_at__isnull=False).exists(),
        "created_at": message.created_at,
    }


def serialize_chat(chat, client, actor, request):
    last = chat.messages.filter(is_deleted=False).select_related("sender").order_by("-created_at").first()
    actor_user = ensure_support_user() if actor == "manager" else client
    membership = chat.members.filter(user=actor_user, is_active=True).first()
    unread = chat.messages.filter(is_deleted=False).exclude(sender=actor_user)
    if membership and membership.last_read_at:
        unread = unread.filter(created_at__gt=membership.last_read_at)
    return {
        "id": str(chat.uuid),
        "sl_id": str(client.username or "").upper(),
        "user": str(client.uuid),
        "user_name": client.get_full_name() or client.username,
        "user_email": client.email,
        "user_activity": None,
        "application": None,
        "application_number": "",
        "assigned_manager": None,
        "status": "open",
        "last_message": serialize_message(last, chat, client, actor, request) if last else None,
        "unread_count": unread.count(),
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
    }


def resolve_client_and_chat(sl_id):
    sl_id = normalize_sl_id(sl_id)
    client = User.objects.filter(username__iexact=sl_id, is_active=True).first()
    chat = support_chat_for(sl_id)
    return sl_id, client, chat


class SLClientProvisionAPIView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not has_sl_service_access(request):
            return service_denied()
        try:
            sl_id = normalize_sl_id(request.data.get("sl_id"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        full_name = str(request.data.get("full_name") or "").strip()
        password = str(request.data.get("password") or "")
        if not full_name or not password:
            return Response({"detail": "full_name and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        client, chat, created, chat_created = provision_client(
            sl_id,
            full_name,
            password,
            request.data.get("email"),
        )
        return Response(
            {
                "status": "created" if created else "exists",
                "chat_status": "created" if chat_created else "exists",
                "sl_id": sl_id,
                "user_uuid": str(client.uuid),
                "chat_uuid": str(chat.uuid),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SLSupportChatListAPIView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not has_sl_service_access(request):
            return service_denied()
        actor = "manager" if request.query_params.get("actor") == "manager" else "client"
        chats = Chat.objects.filter(direct_key__startswith=SUPPORT_CHAT_PREFIX, is_active=True)
        requested_sl_id = str(request.query_params.get("sl_id") or "").strip().casefold()
        if requested_sl_id:
            chats = chats.filter(direct_key=f"{SUPPORT_CHAT_PREFIX}{requested_sl_id}")
        chats = chats.order_by("-last_message_at", "-created_at")
        results = []
        for chat in chats:
            sl_id = chat.direct_key[len(SUPPORT_CHAT_PREFIX):].upper()
            client = User.objects.filter(username__iexact=sl_id).first()
            if client:
                results.append(serialize_chat(chat, client, actor, request))
        return Response({"count": len(results), "results": results})


class SLSupportChatAPIView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request, sl_id):
        if not has_sl_service_access(request):
            return service_denied()
        try:
            _, client, chat = resolve_client_and_chat(sl_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not client or not chat:
            return Response({"detail": "Support chat not found."}, status=status.HTTP_404_NOT_FOUND)
        actor = "manager" if request.query_params.get("actor") == "manager" else "client"
        messages = chat.messages.filter(is_deleted=False).select_related("sender").prefetch_related("receipts", "attachments__media").order_by("created_at")
        return Response({"count": messages.count(), "results": [serialize_message(item, chat, client, actor, request) for item in messages]})

    def post(self, request, sl_id):
        if not has_sl_service_access(request):
            return service_denied()
        try:
            _, client, chat = resolve_client_and_chat(sl_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not client or not chat:
            return Response({"detail": "Support chat not found."}, status=status.HTTP_404_NOT_FOUND)
        actor = "manager" if request.data.get("actor") == "manager" else "client"
        sender = ensure_support_user() if actor == "manager" else client
        text = str(request.data.get("text") or "").strip()
        upload = request.FILES.get("image") or request.FILES.get("file")
        if not text and not upload:
            return Response({"detail": "Text or file is required."}, status=status.HTTP_400_BAD_REQUEST)

        media = None
        if upload:
            try:
                validated = validate_upload_input(upload.name, getattr(upload, "content_type", ""), upload.size)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            suffix = Path(upload.name).suffix[:12].lower()
            saved_name = default_storage.save(f"uploads/{sender.uuid}/{secrets.token_hex(16)}{suffix}", upload)
            media = UploadedMedia.objects.create(
                owner=sender,
                file=saved_name,
                original_name=upload.name[:255],
                content_type=validated.content_type,
                size=validated.size,
                media_kind=validated.media_kind,
                storage_provider=UploadedMedia.StorageProvider.LOCAL,
                object_key=saved_name,
                status=UploadedMedia.Status.UPLOADED,
                processed_at=timezone.now(),
            )

        with transaction.atomic():
            message = Message.objects.create(
                chat=chat,
                sender=sender,
                message_type=media.media_kind if media else Message.MessageType.TEXT,
                text=text,
                metadata={"manager_name": str(request.data.get("manager_name") or "").strip()} if actor == "manager" else {},
            )
            if media:
                MessageAttachment.objects.create(message=message, media=media)
            recipients = list(chat.members.filter(is_active=True).exclude(user=sender).values_list("user_id", flat=True))
            MessageReceipt.objects.bulk_create([MessageReceipt(message=message, user_id=user_id) for user_id in recipients], ignore_conflicts=True)
            chat.last_message_at = message.created_at
            chat.save(update_fields=["last_message_at", "updated_at"])
        message = Message.objects.select_related("sender").prefetch_related("receipts", "attachments__media").get(pk=message.pk)
        return Response(serialize_message(message, chat, client, actor, request), status=status.HTTP_201_CREATED)


class SLSupportChatReadAPIView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, sl_id):
        if not has_sl_service_access(request):
            return service_denied()
        try:
            _, client, chat = resolve_client_and_chat(sl_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not client or not chat:
            return Response({"detail": "Support chat not found."}, status=status.HTTP_404_NOT_FOUND)
        actor = "manager" if request.data.get("actor") == "manager" else "client"
        reader = ensure_support_user() if actor == "manager" else client
        now = timezone.now()
        MessageReceipt.objects.filter(message__chat=chat, user=reader, read_at__isnull=True).update(read_at=now, updated_at=now)
        ChatMember.objects.filter(chat=chat, user=reader, is_active=True).update(last_read_at=now, updated_at=now)
        return Response({"status": "ok"})
