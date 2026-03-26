from django.conf import settings

from apps.common.redis import get_cache_redis, json_dumps
from apps.common.redis_keys import (
    chat_member_permissions_key,
    chat_members_key,
    chat_meta_key,
    user_chats_key,
)


def _chat_ttl() -> int:
    return getattr(settings, "REDIS_CHAT_TTL_SECONDS", 86400)


def serialize_chat(chat) -> dict:
    return {
        "uuid": str(chat.uuid),
        "chat_type": chat.chat_type,
        "title": chat.title or "",
        "description": chat.description or "",
        "avatar": chat.avatar.url if chat.avatar else "",
        "creator_uuid": str(chat.creator.uuid) if chat.creator else "",
        "direct_key": chat.direct_key or "",
        "is_active": chat.is_active,
        "is_public": chat.is_public,
        "members_count": chat.members_count,
        "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
    }


def serialize_chat_member(member) -> dict:
    return {
        "chat_uuid": str(member.chat.uuid),
        "user_uuid": str(member.user.uuid),
        "role": member.role,
        "is_active": member.is_active,
        "is_muted": member.is_muted,
        "can_send_messages": member.can_send_messages,
        "last_read_at": member.last_read_at.isoformat() if member.last_read_at else None,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
    }


def sync_chat_to_redis(chat) -> None:
    client = get_cache_redis()
    ttl = _chat_ttl()
    client.set(chat_meta_key(chat.uuid), json_dumps(serialize_chat(chat)), ex=ttl)


def remove_chat_from_redis(chat_uuid) -> None:
    client = get_cache_redis()
    client.delete(chat_meta_key(chat_uuid))
    client.delete(chat_members_key(chat_uuid))


def sync_chat_member_to_redis(member) -> None:
    client = get_cache_redis()
    ttl = _chat_ttl()

    member_key = chat_member_permissions_key(member.chat.uuid, member.user.uuid)
    members_set_key = chat_members_key(member.chat.uuid)
    user_chats_set_key = user_chats_key(member.user.uuid)

    if member.is_active:
        client.set(member_key, json_dumps(serialize_chat_member(member)), ex=ttl)
        client.sadd(members_set_key, str(member.user.uuid))
        client.sadd(user_chats_set_key, str(member.chat.uuid))
        client.expire(members_set_key, ttl)
        client.expire(user_chats_set_key, ttl)
    else:
        client.delete(member_key)
        client.srem(members_set_key, str(member.user.uuid))
        client.srem(user_chats_set_key, str(member.chat.uuid))


def remove_chat_member_from_redis(chat_uuid, user_uuid) -> None:
    client = get_cache_redis()
    client.delete(chat_member_permissions_key(chat_uuid, user_uuid))
    client.srem(chat_members_key(chat_uuid), str(user_uuid))
    client.srem(user_chats_key(user_uuid), str(chat_uuid))