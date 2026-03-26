from django.conf import settings

from apps.common.redis import get_stream_redis, json_dumps


def publish_realtime_event(event_type: str, chat_uuid: str, payload: dict) -> None:
    channel = getattr(settings, "REDIS_REALTIME_EVENTS_CHANNEL", "realtime:events")
    client = get_stream_redis()

    envelope = {
        "type": event_type,
        "chat_uuid": str(chat_uuid),
        "payload": payload,
    }

    client.publish(channel, json_dumps(envelope))