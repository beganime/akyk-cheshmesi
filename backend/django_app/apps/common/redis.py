import json
import logging
import os
from functools import lru_cache

import redis

logger = logging.getLogger(__name__)


def _build_redis_client(url: str):
    return redis.Redis.from_url(url, decode_responses=True)


@lru_cache(maxsize=1)
def get_cache_redis():
    return _build_redis_client(os.getenv("REDIS_CACHE_URL", "redis://127.0.0.1:6379/0"))


@lru_cache(maxsize=1)
def get_stream_redis():
    return _build_redis_client(os.getenv("REDIS_STREAM_URL", "redis://127.0.0.1:6379/1"))


@lru_cache(maxsize=1)
def get_history_redis():
    return _build_redis_client(os.getenv("REDIS_HISTORY_URL", "redis://127.0.0.1:6379/2"))


def json_dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def json_loads(value, default=None):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception as exc:
        logger.warning("Failed to parse JSON from Redis: %s", exc)
        return default