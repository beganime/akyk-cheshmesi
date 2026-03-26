from django.db import connections
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.redis import get_cache_redis, get_history_redis, get_stream_redis
from apps.common.throttling import BurstScopedRateThrottle


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response(
        {
            "status": "ok",
            "service": "django-core",
            "app": "akyl-chesmesi",
            "api_version": "v1",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BurstScopedRateThrottle])
def readiness(request):
    db_ok = False
    redis_cache_ok = False
    redis_stream_ok = False
    redis_history_ok = False

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except OperationalError:
        db_ok = False

    try:
        redis_cache_ok = get_cache_redis().ping()
    except Exception:
        redis_cache_ok = False

    try:
        redis_stream_ok = get_stream_redis().ping()
    except Exception:
        redis_stream_ok = False

    try:
        redis_history_ok = get_history_redis().ping()
    except Exception:
        redis_history_ok = False

    all_ok = all([db_ok, redis_cache_ok, redis_stream_ok, redis_history_ok])

    payload = {
        "status": "ok" if all_ok else "degraded",
        "service": "django-core",
        "checks": {
            "database": db_ok,
            "redis_cache": redis_cache_ok,
            "redis_stream": redis_stream_ok,
            "redis_history": redis_history_ok,
        },
    }

    return Response(payload, status=200 if all_ok else 503)