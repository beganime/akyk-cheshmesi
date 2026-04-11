from django.conf import settings
from django.utils import timezone

from apps.common.redis import get_cache_redis, json_dumps, json_loads
from apps.common.redis_keys import presence_key


def last_seen_key(user_uuid: str) -> str:
    return f"presence:last-seen:{user_uuid}"


class TrackUserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response

        try:
            client = get_cache_redis()
            user_uuid = str(user.uuid)
            now_iso = timezone.now().isoformat()
            ttl = int(getattr(settings, "REDIS_PRESENCE_TTL_SECONDS", 90))
            last_seen_ttl = max(ttl * 100, 60 * 60 * 24 * 30)

            raw_presence = client.get(presence_key(user_uuid))
            current_presence = json_loads(raw_presence, default=None) or {}

            current_count = current_presence.get("connection_count", 0)
            try:
                current_count = int(current_count or 0)
            except (TypeError, ValueError):
                current_count = 0

            payload = {
                "user_uuid": user_uuid,
                "status": "online" if user.show_online_status else "offline",
                "connection_count": max(current_count, 0),
                "last_seen_at": now_iso,
            }

            client.setex(presence_key(user_uuid), ttl, json_dumps(payload))
            client.setex(last_seen_key(user_uuid), last_seen_ttl, now_iso)
        except Exception:
            # presence tracking must never break a user request
            pass

        return response
