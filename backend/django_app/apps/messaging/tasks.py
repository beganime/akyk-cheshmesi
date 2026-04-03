import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from celery import shared_task
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import service_account

from apps.messaging.models import Message
from apps.users.models import DevicePushToken

logger = logging.getLogger(__name__)

FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def _load_fcm_credentials():
    service_account_json = (os.getenv("FCM_SERVICE_ACCOUNT_JSON") or "").strip()
    service_account_file = (os.getenv("FCM_SERVICE_ACCOUNT_FILE") or "").strip()

    if service_account_json:
        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=FCM_SCOPES)
        project_id = (os.getenv("FCM_PROJECT_ID") or info.get("project_id") or "").strip()
        return credentials, project_id

    if service_account_file:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=FCM_SCOPES,
        )
        project_id = (os.getenv("FCM_PROJECT_ID") or getattr(credentials, "project_id", "") or "").strip()
        return credentials, project_id

    return None, ""


def _get_fcm_access_token():
    credentials, project_id = _load_fcm_credentials()
    if not credentials or not project_id:
        return None, ""

    credentials.refresh(GoogleRequest())
    return credentials.token, project_id


def _build_push_title(message: Message) -> str:
    chat = getattr(message, "chat", None)

    if chat and getattr(chat, "title", ""):
        return str(chat.title)

    sender = getattr(message, "sender", None)
    if not sender:
        return "Новое сообщение"

    return (
        f"{sender.first_name} {sender.last_name}".strip()
        or sender.username
        or sender.email
        or "Новое сообщение"
    )


def _build_push_body(message: Message) -> str:
    text = (message.text or "").strip()
    if text:
        return text[:140]

    if message.message_type == Message.MessageType.IMAGE:
        return "📷 Фото"
    if message.message_type == Message.MessageType.VIDEO:
        return "🎥 Видео"
    if message.message_type == Message.MessageType.AUDIO:
        return "🎤 Голосовое сообщение"
    if message.message_type == Message.MessageType.STICKER:
        return "✨ Стикер"
    if message.message_type == Message.MessageType.FILE:
        return "📎 Файл"

    return "Новое сообщение"


def _send_fcm_message(push_token: DevicePushToken, title: str, body: str, data: dict) -> bool:
    access_token, project_id = _get_fcm_access_token()
    if not access_token or not project_id:
        logger.warning("FCM credentials are not configured")
        return False

    payload = {
        "message": {
            "token": push_token.token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": {key: str(value) for key, value in data.items()},
            "android": {
                "priority": "high",
                "notification": {
                    "channel_id": "messages",
                },
            },
        }
    }

    request = Request(
        url=f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; UTF-8",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            response.read()
        return True
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("FCM HTTPError for token %s: %s | %s", push_token.id, exc.code, response_body)

        if exc.code in {400, 404, 410}:
            push_token.is_active = False
            push_token.save(update_fields=["is_active", "updated_at"])

        return False
    except URLError as exc:
        logger.warning("FCM URLError for token %s: %s", push_token.id, exc)
        return False
    except Exception as exc:
        logger.exception("Unexpected FCM error for token %s: %s", push_token.id, exc)
        return False


@shared_task
def send_new_message_push_notifications(message_id: int) -> int:
    message = (
        Message.objects.select_related("chat", "sender")
        .filter(id=message_id)
        .first()
    )

    if not message or message.is_deleted:
        return 0

    recipient_user_ids = list(
        message.chat.members.filter(is_active=True)
        .exclude(user_id=message.sender_id)
        .values_list("user_id", flat=True)
    )

    if not recipient_user_ids:
        return 0

    push_tokens = list(
        DevicePushToken.objects.filter(
            user_id__in=recipient_user_ids,
            is_active=True,
            provider=DevicePushToken.Provider.FCM,
            platform=DevicePushToken.Platform.ANDROID,
        ).only("id", "token", "user_id", "provider", "platform", "is_active")
    )

    if not push_tokens:
        return 0

    title = _build_push_title(message)
    body = _build_push_body(message)
    data = {
        "chat_uuid": message.chat.uuid,
        "message_uuid": message.uuid,
        "sender_uuid": message.sender.uuid,
        "event": "new_message",
    }

    sent_count = 0

    for push_token in push_tokens:
        if _send_fcm_message(push_token, title, body, data):
            sent_count += 1

    return sent_count