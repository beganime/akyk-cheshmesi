from django.conf import settings

from apps.common.redis import get_history_redis, get_stream_redis, json_dumps
from apps.common.redis_keys import history_last_messages_key, stream_messages_key


def _history_limit() -> int:
    return getattr(settings, "REDIS_HISTORY_LIST_LIMIT", 50)


def _history_ttl() -> int:
    return getattr(settings, "REDIS_HISTORY_TTL_SECONDS", 604800)


def serialize_message_for_cache(message) -> dict:
    return {
        "uuid": str(message.uuid),
        "client_uuid": str(message.client_uuid) if message.client_uuid else None,
        "chat_uuid": str(message.chat.uuid),
        "sender_uuid": str(message.sender.uuid),
        "message_type": message.message_type,
        "text": message.text or "",
        "reply_to_uuid": str(message.reply_to.uuid) if message.reply_to else None,
        "metadata": message.metadata or {},
        "is_edited": message.is_edited,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "is_deleted": message.is_deleted,
        "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
    }


def append_message_to_history_cache(message) -> None:
    client = get_history_redis()
    key = history_last_messages_key(message.chat.uuid)
    payload = json_dumps(serialize_message_for_cache(message))

    client.lpush(key, payload)
    client.ltrim(key, 0, _history_limit() - 1)
    client.expire(key, _history_ttl())


def clear_chat_history_cache(chat_uuid) -> None:
    client = get_history_redis()
    client.delete(history_last_messages_key(chat_uuid))


def build_pending_stream_payload(
    *,
    chat_uuid: str,
    sender_uuid: str,
    text: str,
    message_type: str = "text",
    client_uuid: str | None = None,
    reply_to_uuid: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "event": "pending_save",
        "chat_uuid": str(chat_uuid),
        "sender_uuid": str(sender_uuid),
        "text": text or "",
        "message_type": message_type,
        "client_uuid": str(client_uuid) if client_uuid else "",
        "reply_to_uuid": str(reply_to_uuid) if reply_to_uuid else "",
        "metadata": metadata or {},
    }


def publish_pending_message_to_stream(payload: dict) -> str:
    client = get_stream_redis()
    stream_key = stream_messages_key()

    entry_id = client.xadd(
        stream_key,
        {
            "event": payload.get("event", "pending_save"),
            "chat_uuid": payload.get("chat_uuid", ""),
            "sender_uuid": payload.get("sender_uuid", ""),
            "message_type": payload.get("message_type", "text"),
            "client_uuid": payload.get("client_uuid", ""),
            "reply_to_uuid": payload.get("reply_to_uuid", ""),
            "text": payload.get("text", ""),
            "metadata": json_dumps(payload.get("metadata", {})),
            "payload": json_dumps(payload),
        },
    )
    return entry_id