from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.response import Response

from apps.common.redis import get_cache_redis, json_loads
from apps.common.redis_keys import presence_key
from .presence_policy import can_view_presence

User = get_user_model()


def build_offline_payload(user_uuid: str, last_seen_at=None):
    return {
        "user_uuid": str(user_uuid),
        "status": "offline",
        "connection_count": 0,
        "last_seen_at": last_seen_at,
    }


class PresenceDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_uuid = str(kwargs["user_uuid"])

        target_user = User.objects.filter(uuid=user_uuid, is_active=True).first()
        if not target_user:
            return Response({"detail": "User not found"}, status=404)
        if not can_view_presence(request.user, target_user):
            return Response(build_offline_payload(user_uuid), status=200)

        raw = get_cache_redis().get(presence_key(user_uuid))
        payload = json_loads(raw, default=None) or build_offline_payload(user_uuid, target_user.last_login)

        return Response(payload, status=200)


class PresenceBulkAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_uuid_values = request.query_params.getlist("user_uuid")
        unique_values = []
        seen = set()

        for value in user_uuid_values:
            value = value.strip()
            if value and value not in seen:
                seen.add(value)
                unique_values.append(value)

        if not unique_values:
            return Response({"results": []}, status=200)

        existing_users = {
            str(user.uuid): user
            for user in User.objects.filter(uuid__in=unique_values, is_active=True)
        }

        client = get_cache_redis()
        results = []

        for user_uuid in unique_values:
            target_user = existing_users.get(user_uuid)
            if not target_user:
                continue
            if not can_view_presence(request.user, target_user):
                results.append(build_offline_payload(user_uuid))
                continue

            raw = client.get(presence_key(user_uuid))
            payload = json_loads(raw, default=None) or build_offline_payload(user_uuid, target_user.last_login)
            results.append(payload)

        return Response({"results": results}, status=200)
