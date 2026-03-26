from django.conf import settings

from apps.common.redis import get_cache_redis, json_dumps
from apps.common.redis_keys import auth_user_email_key, auth_user_key


def sync_user_to_redis(user) -> None:
    payload = {
        "uuid": str(user.uuid),
        "email": user.email,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "avatar": user.avatar.url if user.avatar else "",
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "registration_completed": user.registration_completed,
    }

    ttl = getattr(settings, "REDIS_PROFILE_TTL_SECONDS", 86400)
    client = get_cache_redis()

    client.set(auth_user_key(user.uuid), json_dumps(payload), ex=ttl)
    client.set(auth_user_email_key(user.email), str(user.uuid), ex=ttl)