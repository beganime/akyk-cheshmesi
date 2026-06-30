import json
import logging
import time
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from django.conf import settings
from django.db import transaction

from apps.users.models import DevicePushToken

logger = logging.getLogger(__name__)

FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


@dataclass
class PushDispatchResult:
    attempted_count: int = 0
    sent_count: int = 0
    skipped_count: int = 0
    disabled: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def push_is_enabled() -> bool:
    return bool(getattr(settings, "FCM_ENABLED", False) or getattr(settings, "APNS_ENABLED", False))


def _fcm_is_enabled() -> bool:
    return bool(getattr(settings, "FCM_ENABLED", False))


def _apns_is_enabled() -> bool:
    return bool(getattr(settings, "APNS_ENABLED", False))


def _load_fcm_credentials():
    from google.oauth2 import service_account

    service_account_json = (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
    credentials_path = (getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or "").strip()

    if service_account_json:
        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=FCM_SCOPES)
        project_id = (getattr(settings, "FCM_PROJECT_ID", "") or info.get("project_id") or "").strip()
        return credentials, project_id

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=FCM_SCOPES)
        project_id = (getattr(settings, "FCM_PROJECT_ID", "") or getattr(credentials, "project_id", "") or "").strip()
        return credentials, project_id

    return None, ""


def _get_fcm_access_token():
    if not _fcm_is_enabled():
        return None, ""

    try:
        from google.auth.transport.requests import Request as GoogleRequest

        credentials, project_id = _load_fcm_credentials()
        if not credentials or not project_id:
            logger.warning("FCM is enabled but Firebase credentials/project id are not configured")
            return None, ""
        credentials.refresh(GoogleRequest())
        return credentials.token, project_id
    except Exception as exc:
        logger.exception("Failed to load Firebase credentials: %s", exc)
        return None, ""


def _stringify_data(data: dict) -> dict[str, str]:
    return {str(key): "" if value is None else str(value) for key, value in (data or {}).items()}


def _notification_channel_id(data: dict) -> str:
    push_type = str((data or {}).get("type") or "")
    if push_type in {"call", "incoming_call", "missed_call"}:
        return "calls"
    return "messages"


def _is_call_push(data: dict) -> bool:
    return str((data or {}).get("type") or "") in {"call", "incoming_call"}


def _fcm_payload(push_token: DevicePushToken, title: str, body: str, data: dict) -> dict:
    channel_id = _notification_channel_id(data)
    data = {**(data or {}), "channel_id": channel_id}
    android_config = {
        "priority": "high",
        "notification": {
            "channel_id": channel_id,
            "sound": "default",
        },
    }
    if _is_call_push(data):
        android_config["ttl"] = "60s"

    aps = {
        "sound": "default",
        "content-available": 1,
    }
    if channel_id == "calls":
        aps["interruption-level"] = "time-sensitive"

    return {
        "message": {
            "token": push_token.token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": _stringify_data(data),
            "android": android_config,
            "apns": {
                "headers": {
                    "apns-priority": "10",
                    "apns-push-type": "alert",
                },
                "payload": {
                    "aps": aps,
                },
            },
        }
    }


def _is_invalid_fcm_response(status_code: int, response_body: str) -> bool:
    body = response_body.upper()
    invalid_markers = (
        "UNREGISTERED",
        "INVALID_ARGUMENT",
        "REGISTRATION_TOKEN_NOT_REGISTERED",
        "INVALID_REGISTRATION",
        "NOT_FOUND",
    )
    return status_code in {404, 410} or any(marker in body for marker in invalid_markers)


def _deactivate_token(push_token: DevicePushToken, reason: str) -> None:
    push_token.is_active = False
    meta = push_token.meta or {}
    meta["deactivated_reason"] = reason
    push_token.meta = meta
    push_token.save(update_fields=["is_active", "meta", "updated_at"])


def _send_fcm_message(push_token: DevicePushToken, title: str, body: str, data: dict) -> bool:
    access_token, project_id = _get_fcm_access_token()
    if not access_token or not project_id:
        return False

    request = UrlRequest(
        url=f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        data=json.dumps(_fcm_payload(push_token, title, body, data)).encode("utf-8"),
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
        logger.warning("FCM HTTP error for push token %s: %s | %s", push_token.id, exc.code, response_body)
        if _is_invalid_fcm_response(exc.code, response_body):
            _deactivate_token(push_token, "fcm_invalid_token")
        return False
    except URLError as exc:
        logger.warning("FCM URL error for push token %s: %s", push_token.id, exc)
        return False
    except Exception as exc:
        logger.exception("Unexpected FCM error for push token %s: %s", push_token.id, exc)
        return False


def _load_apns_auth_key() -> str:
    auth_key = (getattr(settings, "APNS_AUTH_KEY", "") or "").strip()
    if auth_key:
        return auth_key.replace("\\n", "\n")

    auth_key_path = (getattr(settings, "APNS_AUTH_KEY_PATH", "") or "").strip()
    if auth_key_path:
        with open(auth_key_path, "r", encoding="utf-8") as key_file:
            return key_file.read()

    return ""


def _get_apns_auth_token() -> str:
    if not _apns_is_enabled():
        return ""

    team_id = (getattr(settings, "APNS_TEAM_ID", "") or "").strip()
    key_id = (getattr(settings, "APNS_KEY_ID", "") or "").strip()
    auth_key = _load_apns_auth_key()
    if not team_id or not key_id or not auth_key:
        logger.warning("APNS is enabled but team id, key id, or auth key is missing")
        return ""

    try:
        import jwt

        return jwt.encode(
            {"iss": team_id, "iat": int(time.time())},
            auth_key,
            algorithm="ES256",
            headers={"kid": key_id},
        )
    except Exception as exc:
        logger.exception("Failed to build APNS auth token: %s", exc)
        return ""


def _apns_payload(title: str, body: str, data: dict) -> dict:
    channel_id = _notification_channel_id(data)
    data = {**(data or {}), "channel_id": channel_id}
    aps = {
        "alert": {
            "title": title,
            "body": body,
        },
        "sound": "default",
        "content-available": 1,
    }
    if channel_id == "calls":
        aps["interruption-level"] = "time-sensitive"

    return {
        "aps": aps,
        **_stringify_data(data),
    }


def _send_apns_message(push_token: DevicePushToken, title: str, body: str, data: dict) -> bool:
    auth_token = _get_apns_auth_token()
    bundle_id = (getattr(settings, "APNS_BUNDLE_ID", "") or "").strip()
    if not auth_token or not bundle_id:
        return False

    host = (
        "https://api.sandbox.push.apple.com"
        if getattr(settings, "APNS_USE_SANDBOX", False)
        else "https://api.push.apple.com"
    )
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "apns-topic": bundle_id,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    if _is_call_push(data):
        headers["apns-expiration"] = str(int(time.time()) + 60)

    request = UrlRequest(
        url=f"{host}/3/device/{push_token.token}",
        data=json.dumps(_apns_payload(title, body, data)).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            response.read()
        return True
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("APNS HTTP error for push token %s: %s | %s", push_token.id, exc.code, response_body)
        if exc.code in {400, 410}:
            _deactivate_token(push_token, "apns_invalid_token")
        return False
    except URLError as exc:
        logger.warning("APNS URL error for push token %s: %s", push_token.id, exc)
        return False
    except Exception as exc:
        logger.exception("Unexpected APNS error for push token %s: %s", push_token.id, exc)
        return False


def _send_device_push(push_token: DevicePushToken, title: str, body: str, data: dict) -> bool:
    if push_token.provider == DevicePushToken.Provider.FCM:
        if not _fcm_is_enabled():
            logger.info("Skipping FCM token because FCM is disabled: token=%s", push_token.id)
            return False
        return _send_fcm_message(push_token, title, body, data)

    if push_token.provider == DevicePushToken.Provider.APNS:
        if not _apns_is_enabled():
            logger.info("Skipping APNS token because APNS is disabled: token=%s", push_token.id)
            return False
        return _send_apns_message(push_token, title, body, data)

    logger.info("Skipping unsupported push provider=%s token=%s", push_token.provider, push_token.id)
    return False


def send_push_to_user_ids(user_ids, title: str, body: str, data: dict) -> PushDispatchResult:
    user_ids = [user_id for user_id in dict.fromkeys(user_ids or []) if user_id]
    if not user_ids:
        logger.info("Push skipped: no recipient users | type=%s", (data or {}).get("type", ""))
        return PushDispatchResult()

    if not push_is_enabled():
        logger.info("Push providers are disabled; skipping push to %s users", len(user_ids))
        return PushDispatchResult(disabled=True, skipped_count=len(user_ids))

    push_tokens = list(
        DevicePushToken.objects.filter(user_id__in=user_ids, is_active=True).only(
            "id",
            "token",
            "user_id",
            "provider",
            "platform",
            "is_active",
            "meta",
        )
    )
    result = PushDispatchResult(attempted_count=len(push_tokens))
    if not push_tokens:
        logger.info("Push skipped: no active tokens | type=%s users=%s", (data or {}).get("type", ""), len(user_ids))
        return result

    for push_token in push_tokens:
        if push_token.provider not in {DevicePushToken.Provider.FCM, DevicePushToken.Provider.APNS}:
            result.skipped_count += 1
            logger.info("Skipping unsupported push provider=%s token=%s", push_token.provider, push_token.id)
            continue
        if push_token.provider == DevicePushToken.Provider.FCM and not _fcm_is_enabled():
            result.skipped_count += 1
            logger.info("Skipping FCM token because FCM is disabled: token=%s", push_token.id)
            continue
        if push_token.provider == DevicePushToken.Provider.APNS and not _apns_is_enabled():
            result.skipped_count += 1
            logger.info("Skipping APNS token because APNS is disabled: token=%s", push_token.id)
            continue

        if _send_device_push(push_token, title, body, data):
            result.sent_count += 1

    logger.info(
        "Push sent | type=%s users=%s tokens=%s sent=%s skipped=%s",
        (data or {}).get("type", ""),
        len(user_ids),
        result.attempted_count,
        result.sent_count,
        result.skipped_count,
    )
    return result


def dispatch_push_to_user_ids(user_ids, title: str, body: str, data: dict) -> None:
    user_ids = [user_id for user_id in dict.fromkeys(user_ids or []) if user_id]
    if not user_ids:
        return

    if not push_is_enabled():
        logger.info("Push providers are disabled; not enqueueing push to %s users", len(user_ids))
        return

    def deliver_after_commit():
        if getattr(settings, "TASKS_EAGER", False) or not getattr(settings, "PUSH_NOTIFICATIONS_ASYNC", True):
            send_push_to_user_ids(user_ids, title, body, data)
            return

        try:
            from apps.users.tasks import send_push_notification

            send_push_notification.delay(user_ids, title, body, data)
        except Exception:
            logger.exception("Failed to enqueue push task; sending synchronously")
            send_push_to_user_ids(user_ids, title, body, data)

    transaction.on_commit(deliver_after_commit)


def _user_display_name(user) -> str:
    return (
        f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        or getattr(user, "username", "")
        or getattr(user, "email", "")
        or "Akyl Cheshmesi"
    )


def _message_push_body(message) -> str:
    text = (message.text or "").strip()
    if text:
        return text[:140]

    labels = {
        "image": "Photo",
        "video": "Video",
        "audio": "Voice message",
        "video_note": "Video note",
        "file": "File",
        "sticker": "Sticker",
    }
    return labels.get(message.message_type, "New message")


def send_message_push_by_id(message_id: int) -> PushDispatchResult:
    from apps.chats.models import ChatMember
    from apps.messaging.models import Message

    message = Message.objects.select_related("chat", "sender").filter(id=message_id).first()
    if not message or message.is_deleted:
        return PushDispatchResult()

    recipient_user_ids = list(
        ChatMember.objects.filter(chat=message.chat, is_active=True, is_muted=False, is_archived=False)
        .exclude(user_id=message.sender_id)
        .values_list("user_id", flat=True)
    )
    if not recipient_user_ids:
        return PushDispatchResult()

    metadata = message.metadata or {}
    story_uuid = metadata.get("story_uuid") or ""
    story_action = metadata.get("story_action") or ""
    push_type = "story_reply" if story_action == "reply" else "story_reaction" if story_action == "reaction" else "message"

    title = message.chat.title or _user_display_name(message.sender)
    body = _message_push_body(message)
    data = {
        "type": push_type,
        "chat_uuid": str(message.chat.uuid),
        "message_uuid": str(message.uuid),
        "sender_uuid": str(message.sender.uuid),
        "sender_name": _user_display_name(message.sender),
        "message_type": message.message_type,
        "preview": body,
    }
    if story_uuid:
        data["story_uuid"] = str(story_uuid)
    if story_action:
        data["story_action"] = str(story_action)

    return send_push_to_user_ids(recipient_user_ids, title, body, data)


def dispatch_call_push(session_id: int, push_type: str, actor_user_id: int | None = None) -> None:
    from apps.calls.models import CallSession
    from apps.chats.models import ChatMember

    session = CallSession.objects.select_related("chat", "initiated_by").filter(id=session_id).first()
    if not session:
        return

    recipients = ChatMember.objects.filter(chat=session.chat, is_active=True, is_muted=False, is_archived=False)
    if push_type == "call":
        recipients = recipients.exclude(user_id=session.initiated_by_id)
    elif actor_user_id:
        recipients = recipients.exclude(user_id=actor_user_id)

    recipient_user_ids = list(recipients.values_list("user_id", flat=True))
    if not recipient_user_ids:
        return

    caller_name = _user_display_name(session.initiated_by)
    if push_type == "missed_call":
        title = "Missed call"
        body = f"Missed {session.call_type} call"
    else:
        title = "Incoming call"
        body = f"{caller_name} is calling"

    caller_uuid = str(session.initiated_by.uuid)
    dispatch_push_to_user_ids(
        recipient_user_ids,
        title,
        body,
        {
            "type": push_type,
            "event": "incoming_call" if push_type == "call" else push_type,
            "chat_uuid": str(session.chat.uuid),
            "call_uuid": str(session.uuid),
            "room_key": session.room_key,
            "call_type": session.call_type,
            "status": session.status,
            "initiated_by_uuid": caller_uuid,
            "caller_uuid": caller_uuid,
            "caller_name": caller_name,
        },
    )
