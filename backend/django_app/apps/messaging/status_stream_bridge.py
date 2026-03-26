import json
import logging
import socket
import uuid
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from redis.exceptions import ResponseError

from apps.chats.models import ChatMember
from apps.common.redis import get_stream_redis
from apps.messaging.models import Message, MessageReceipt
from apps.messaging.realtime_events import publish_realtime_event
from apps.users.models import User

logger = logging.getLogger(__name__)


class PermanentStatusError(Exception):
    pass


@dataclass
class StatusProcessResult:
    entry_id: str
    status: str
    detail: str
    event_type: str
    message_uuid: str | None = None


class MessageStatusStreamSaver:
    def __init__(
        self,
        *,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        dlq_key: str,
    ):
        self.redis = get_stream_redis()
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.dlq_key = dlq_key

    @staticmethod
    def build_default_consumer_name() -> str:
        return f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    def ensure_group(self) -> None:
        try:
            self.redis.xgroup_create(
                name=self.stream_key,
                groupname=self.group_name,
                id="0",
                mkstream=True,
            )
            logger.info("Created Redis consumer group %s for %s", self.group_name, self.stream_key)
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.info("Redis consumer group already exists: %s", self.group_name)
                return
            raise

    def consume_forever(
        self,
        *,
        block_ms: int = 5000,
        count: int = 50,
        claim_idle_ms: int = 60000,
    ) -> None:
        self.ensure_group()
        logger.info(
            "Starting status saver | stream=%s group=%s consumer=%s",
            self.stream_key,
            self.group_name,
            self.consumer_name,
        )

        while True:
            self._claim_stale_pending(claim_idle_ms=claim_idle_ms, count=count)

            entries = self.redis.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_key: ">"},
                count=count,
                block=block_ms,
            )

            if not entries:
                continue

            for _, messages in entries:
                for entry_id, fields in messages:
                    self._handle_entry(entry_id, fields)

    def consume_once(
        self,
        *,
        count: int = 50,
        claim_idle_ms: int = 60000,
    ) -> int:
        self.ensure_group()

        processed = 0
        self._claim_stale_pending(claim_idle_ms=claim_idle_ms, count=count)

        entries = self.redis.xreadgroup(
            groupname=self.group_name,
            consumername=self.consumer_name,
            streams={self.stream_key: ">"},
            count=count,
            block=1000,
        )

        for _, messages in entries:
            for entry_id, fields in messages:
                self._handle_entry(entry_id, fields)
                processed += 1

        return processed

    def _claim_stale_pending(self, *, claim_idle_ms: int, count: int) -> None:
        try:
            result = self.redis.xautoclaim(
                name=self.stream_key,
                groupname=self.group_name,
                consumername=self.consumer_name,
                min_idle_time=claim_idle_ms,
                start_id="0-0",
                count=count,
            )
        except Exception as exc:
            logger.warning("status xautoclaim failed: %s", exc)
            return

        if not result or len(result) < 2:
            return

        claimed_messages = result[1] or []
        for entry_id, fields in claimed_messages:
            logger.info("Claimed stale status entry: %s", entry_id)
            self._handle_entry(entry_id, fields)

    def _handle_entry(self, entry_id: str, fields: dict[str, Any]) -> None:
        try:
            result = self._process_entry(entry_id, fields)
            self.redis.xack(self.stream_key, self.group_name, entry_id)

            logger.info(
                "Processed status entry | entry_id=%s status=%s detail=%s event=%s message_uuid=%s",
                result.entry_id,
                result.status,
                result.detail,
                result.event_type,
                result.message_uuid,
            )

        except PermanentStatusError as exc:
            self._move_to_dlq(entry_id, fields, str(exc))
            self.redis.xack(self.stream_key, self.group_name, entry_id)
            logger.warning("Moved status entry to DLQ | entry_id=%s reason=%s", entry_id, exc)

        except Exception as exc:
            logger.exception("Transient status processing error for entry %s: %s", entry_id, exc)

    def _move_to_dlq(self, entry_id: str, fields: dict[str, Any], reason: str) -> None:
        self.redis.xadd(
            self.dlq_key,
            {
                "entry_id": entry_id,
                "reason": reason,
                "raw_fields": json.dumps(fields, ensure_ascii=False, default=str),
            },
        )

    def _parse_payload(self, fields: dict[str, Any]) -> dict[str, Any]:
        raw_payload = fields.get("payload")

        if raw_payload:
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError as exc:
                raise PermanentStatusError(f"Invalid payload JSON: {exc}") from exc
        else:
            payload = {
                "event": fields.get("event", ""),
                "chat_uuid": fields.get("chat_uuid", ""),
                "message_uuid": fields.get("message_uuid", ""),
                "user_uuid": fields.get("user_uuid", ""),
                "device_id": fields.get("device_id", ""),
                "sent_at": fields.get("sent_at", ""),
            }

        event = payload.get("event", "")
        if event not in {"delivered", "read"}:
            raise PermanentStatusError(f"Unsupported status event: {event}")

        if not payload.get("chat_uuid"):
            raise PermanentStatusError("chat_uuid is missing")
        if not payload.get("message_uuid"):
            raise PermanentStatusError("message_uuid is missing")
        if not payload.get("user_uuid"):
            raise PermanentStatusError("user_uuid is missing")

        return payload

    def _process_entry(self, entry_id: str, fields: dict[str, Any]) -> StatusProcessResult:
        payload = self._parse_payload(fields)

        event = payload["event"]
        chat_uuid = payload["chat_uuid"]
        message_uuid = payload["message_uuid"]
        user_uuid = payload["user_uuid"]

        message = (
            Message.objects.select_related("chat", "sender")
            .filter(uuid=message_uuid, chat__uuid=chat_uuid)
            .first()
        )
        if not message:
            raise PermanentStatusError("Message not found in chat")

        user = User.objects.filter(
            uuid=user_uuid,
            is_active=True,
            is_email_verified=True,
            registration_completed=True,
        ).first()
        if not user:
            raise PermanentStatusError("User not found or inactive")

        membership = ChatMember.objects.filter(chat=message.chat, user=user, is_active=True).first()
        if not membership:
            raise PermanentStatusError("User is not an active chat member")

        if message.sender_id == user.id:
            raise PermanentStatusError("Sender cannot mark own message as delivered/read")

        now = timezone.now()

        with transaction.atomic():
            receipt, _ = MessageReceipt.objects.get_or_create(
                message=message,
                user=user,
            )

            changed = False

            if event == "delivered":
                if receipt.delivered_at is None:
                    receipt.delivered_at = now
                    receipt.save(update_fields=["delivered_at", "updated_at"])
                    changed = True

                publish_realtime_event(
                    "message_delivered",
                    str(message.chat.uuid),
                    {
                        "message_uuid": str(message.uuid),
                        "chat_uuid": str(message.chat.uuid),
                        "user_uuid": str(user.uuid),
                        "delivered_at": (receipt.delivered_at or now).isoformat(),
                    },
                )

                return StatusProcessResult(
                    entry_id=entry_id,
                    status="updated" if changed else "noop",
                    detail="Delivered status processed",
                    event_type=event,
                    message_uuid=str(message.uuid),
                )

            if receipt.delivered_at is None:
                receipt.delivered_at = now
                changed = True

            if receipt.read_at is None:
                receipt.read_at = now
                changed = True

            receipt.save(update_fields=["delivered_at", "read_at", "updated_at"])

            if membership.last_read_at is None or membership.last_read_at < now:
                membership.last_read_at = now
                membership.save(update_fields=["last_read_at", "updated_at"])

            publish_realtime_event(
                "message_read",
                str(message.chat.uuid),
                {
                    "message_uuid": str(message.uuid),
                    "chat_uuid": str(message.chat.uuid),
                    "user_uuid": str(user.uuid),
                    "read_at": (receipt.read_at or now).isoformat(),
                    "delivered_at": (receipt.delivered_at or now).isoformat(),
                },
            )

            return StatusProcessResult(
                entry_id=entry_id,
                status="updated" if changed else "noop",
                detail="Read status processed",
                event_type=event,
                message_uuid=str(message.uuid),
            )