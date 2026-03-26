from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.response import Response

from apps.common.redis import get_cache_redis, json_loads
from apps.common.redis_keys import presence_key

User = get_user_model()


def build_offline_payload(user_uuid: str):
    return {
        "user_uuid": str(user_uuid),
        "status": "offline",
        "connection_count": 0,
        "last_seen_at": None,
    }


class PresenceDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_uuid = str(kwargs["user_uuid"])

        user_exists = User.objects.filter(uuid=user_uuid, is_active=True).exists()
        if not user_exists:
            return Response({"detail": "User not found"}, status=404)

        raw = get_cache_redis().get(presence_key(user_uuid))
        payload = json_loads(raw, default=None) or build_offline_payload(user_uuid)

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

        existing_user_uuids = set(
            str(value)
            for value in User.objects.filter(uuid__in=unique_values, is_active=True).values_list("uuid", flat=True)
        )

        client = get_cache_redis()
        results = []

        for user_uuid in unique_values:
            if user_uuid not in existing_user_uuids:
                continue

            raw = client.get(presence_key(user_uuid))
            payload = json_loads(raw, default=None) or build_offline_payload(user_uuid)
            results.append(payload)

        return Response({"results": results}, status=200)