import os


def auth_user_key(user_uuid) -> str:
    return f"auth:user:{user_uuid}"


def auth_user_email_key(email: str) -> str:
    return f"auth:user-email:{email.lower()}"


def chat_meta_key(chat_uuid) -> str:
    return f"chat:meta:{chat_uuid}"


def chat_members_key(chat_uuid) -> str:
    return f"chat:members:{chat_uuid}"


def chat_member_permissions_key(chat_uuid, user_uuid) -> str:
    return f"chat:member:{chat_uuid}:{user_uuid}"


def user_chats_key(user_uuid) -> str:
    return f"user:chats:{user_uuid}"


def history_last_messages_key(chat_uuid) -> str:
    return f"history:last:{chat_uuid}"


def presence_key(user_uuid) -> str:
    return f"presence:{user_uuid}"


def stream_messages_key() -> str:
    return os.getenv("REDIS_STREAM_MESSAGES_KEY", "stream:messages")