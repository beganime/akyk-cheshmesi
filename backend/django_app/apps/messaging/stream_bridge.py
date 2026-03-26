import json
import logging
import socket
import uuid
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from redis.exceptions import ResponseError

from apps.chats.models import Chat, ChatMember
from apps.common.redis import get_stream_redis
from apps.mediafiles.models import MessageAttachment, UploadedMedia
from apps.messaging.models import Message, MessageReceipt
from apps.messaging.realtime_events import publish_realtime_event
from apps.users.models import User

logger = logging.getLogger(__name__)


class PermanentStreamError(Exception):
    pass


@dataclass
class ProcessResult:
    entry_id: str
    status: str
    detail: str
    message_uuid: str | None = None
    created: bool = False


class MessageStreamSaver:
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
        count: int = 20,
        claim_idle_ms: int = 60000,
    ) -> None:
        self.ensure_group()
        logger.info(
            "Starting saver consumer | stream=%s group=%s consumer=%s",
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
        count: int = 20,
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
            logger.warning("xautoclaim failed: %s", exc)
            return

        if not result or len(result) < 2:
            return

        claimed_messages = result[1] or []
        for entry_id, fields in claimed_messages:
            logger.info("Claimed stale pending message: %s", entry_id)
            self._handle_entry(entry_id, fields)

    def _handle_entry(self, entry_id: str, fields: dict[str, Any]) -> None:
        try:
            result = self._process_entry(entry_id, fields)
            self.redis.xack(self.stream_key, self.group_name, entry_id)

            logger.info(
                "Processed stream entry | entry_id=%s status=%s detail=%s message_uuid=%s created=%s",
                result.entry_id,
                result.status,
                result.detail,
                result.message_uuid,
                result.created,
            )

        except PermanentStreamError as exc:
            self._move_to_dlq(entry_id, fields, str(exc))
            self.redis.xack(self.stream_key, self.group_name, entry_id)
            logger.warning("Moved message to DLQ | entry_id=%s reason=%s", entry_id, exc)

        except Exception as exc:
            logger.exception("Transient processing error for entry %s: %s", entry_id, exc)

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
                raise PermanentStreamError(f"Invalid payload JSON: {exc}") from exc
        else:
            payload = {
                "event": fields.get("event", "pending_save"),
                "chat_uuid": fields.get("chat_uuid", ""),
                "sender_uuid": fields.get("sender_uuid", ""),
                "sender_email": fields.get("sender_email", ""),
                "sender_username": fields.get("sender_username", ""),
                "message_type": fields.get("message_type", "text"),
                "client_uuid": fields.get("client_uuid", ""),
                "reply_to_uuid": fields.get("reply_to_uuid", ""),
                "text": fields.get("text", ""),
                "payload": {},
                "sent_at": fields.get("sent_at", ""),
            }

        if not payload.get("chat_uuid"):
            raise PermanentStreamError("chat_uuid is missing")
        if not payload.get("sender_uuid"):
            raise PermanentStreamError("sender_uuid is missing")

        message_type = payload.get("message_type") or "text"
        allowed_types = {choice[0] for choice in Message.MessageType.choices}
        if message_type not in allowed_types:
            raise PermanentStreamError(f"Unsupported message_type: {message_type}")

        text = (payload.get("text") or "").strip()
        payload_data = payload.get("payload") or {}
        if not isinstance(payload_data, dict):
            raise PermanentStreamError("payload must be a JSON object")

        payload["message_type"] = message_type
        payload["text"] = text
        payload["payload"] = payload_data

        if message_type == Message.MessageType.TEXT and not text and not payload_data.get("attachment_uuids"):
            raise PermanentStreamError("Text is required for text messages without attachments")

        return payload

    def _extract_attachment_uuid_values(self, payload_data: dict[str, Any]) -> list[str]:
        raw_values = payload_data.pop("attachment_uuids", [])
        if not raw_values:
            return []

        if not isinstance(raw_values, list):
            raise PermanentStreamError("attachment_uuids must be a list")

        normalized = []
        seen = set()

        for value in raw_values:
            try:
                parsed = str(uuid.UUID(str(value)))
            except ValueError as exc:
                raise PermanentStreamError(f"Invalid attachment uuid: {value}") from exc

            if parsed not in seen:
                seen.add(parsed)
                normalized.append(parsed)

        return normalized

    def _resolve_uploaded_media(self, sender: User, attachment_uuid_values: list[str]) -> list[UploadedMedia]:
        if not attachment_uuid_values:
            return []

        media_queryset = UploadedMedia.objects.filter(
            uuid__in=attachment_uuid_values,
            owner=sender,
            status=UploadedMedia.Status.UPLOADED,
        )

        media_map = {str(media.uuid): media for media in media_queryset}
        ordered_media = []

        for attachment_uuid in attachment_uuid_values:
            media = media_map.get(attachment_uuid)
            if not media:
                raise PermanentStreamError(f"Uploaded media not found or not ready: {attachment_uuid}")
            ordered_media.append(media)

        return ordered_media

    def _build_attachment_payloads(self, message: Message) -> list[dict[str, Any]]:
        attachments = (
            message.attachments.select_related("media")
            .all()
            .order_by("sort_order", "id")
        )

        items = []
        for attachment in attachments:
            media = attachment.media
            file_url = None
            if media.file:
                try:
                    file_url = media.file.url
                except Exception:
                    file_url = None
            if not file_url:
                file_url = media.meta.get("file_url")

            items.append(
                {
                    "uuid": str(media.uuid),
                    "original_name": media.original_name,
                    "content_type": media.content_type,
                    "size": media.size,
                    "media_kind": media.media_kind,
                    "file_url": file_url,
                }
            )
        return items

    def _emit_persisted_event(
        self,
        *,
        message: Message,
        client_uuid: str | None,
        entry_id: str,
        persisted_status: str,
    ) -> None:
        publish_realtime_event(
            "message_persisted",
            str(message.chat.uuid),
            {
                "message_uuid": str(message.uuid),
                "chat_uuid": str(message.chat.uuid),
                "sender_uuid": str(message.sender.uuid),
                "client_uuid": client_uuid or "",
                "message_type": message.message_type,
                "text": message.text or "",
                "attachments": self._build_attachment_payloads(message),
                "stream_entry_id": entry_id,
                "persisted_status": persisted_status,
                "persisted_at": message.created_at.isoformat(),
            },
        )

    def _process_entry(self, entry_id: str, fields: dict[str, Any]) -> ProcessResult:
        payload = self._parse_payload(fields)

        chat_uuid = payload["chat_uuid"]
        sender_uuid = payload["sender_uuid"]
        client_uuid_raw = payload.get("client_uuid") or None
        reply_to_uuid_raw = payload.get("reply_to_uuid") or None

        try:
            client_uuid = uuid.UUID(client_uuid_raw) if client_uuid_raw else None
        except ValueError as exc:
            raise PermanentStreamError("Invalid client_uuid") from exc

        try:
            reply_to_uuid = uuid.UUID(reply_to_uuid_raw) if reply_to_uuid_raw else None
        except ValueError as exc:
            raise PermanentStreamError("Invalid reply_to_uuid") from exc

        chat = Chat.objects.filter(uuid=chat_uuid, is_active=True).first()
        if not chat:
            raise PermanentStreamError("Chat not found or inactive")

        sender = User.objects.filter(
            uuid=sender_uuid,
            is_active=True,
            is_email_verified=True,
            registration_completed=True,
        ).first()
        if not sender:
            raise PermanentStreamError("Sender not found or inactive")

        membership = ChatMember.objects.filter(chat=chat, user=sender, is_active=True).first()
        if not membership:
            raise PermanentStreamError("Sender is not an active chat member")

        if not membership.can_send_messages:
            raise PermanentStreamError("Sender is not allowed to send messages")

        reply_to = None
        if reply_to_uuid:
            reply_to = Message.objects.filter(chat=chat, uuid=reply_to_uuid).first()
            if not reply_to:
                raise PermanentStreamError("Reply target not found in this chat")

        existing = None
        if client_uuid:
            existing = Message.objects.filter(client_uuid=client_uuid).first()

        if existing:
            self._emit_persisted_event(
                message=existing,
                client_uuid=client_uuid_raw,
                entry_id=entry_id,
                persisted_status="duplicate",
            )
            return ProcessResult(
                entry_id=entry_id,
                status="duplicate",
                detail="Message already persisted earlier",
                message_uuid=str(existing.uuid),
                created=False,
            )

        payload_data = payload.get("payload", {})
        attachment_uuid_values = self._extract_attachment_uuid_values(payload_data)
        uploaded_media = self._resolve_uploaded_media(sender, attachment_uuid_values)

        metadata = {
            **payload_data,
            "_stream_entry_id": entry_id,
            "_queued_at": payload.get("sent_at") or "",
        }

        with transaction.atomic():
            message = Message.objects.create(
                chat=chat,
                sender=sender,
                client_uuid=client_uuid,
                message_type=payload["message_type"],
                text=payload["text"],
                reply_to=reply_to,
                metadata=metadata,
            )

            if uploaded_media:
                MessageAttachment.objects.bulk_create(
                    [
                        MessageAttachment(
                            message=message,
                            media=media,
                            sort_order=index,
                        )
                        for index, media in enumerate(uploaded_media)
                    ],
                    ignore_conflicts=True,
                )

            recipient_ids = list(
                chat.members.filter(is_active=True)
                .exclude(user_id=sender.id)
                .values_list("user_id", flat=True)
            )

            if recipient_ids:
                MessageReceipt.objects.bulk_create(
                    [
                        MessageReceipt(
                            message=message,
                            user_id=user_id,
                        )
                        for user_id in recipient_ids
                    ],
                    ignore_conflicts=True,
                )

            if chat.last_message_at != message.created_at:
                chat.last_message_at = message.created_at
                chat.save(update_fields=["last_message_at", "updated_at"])

        self._emit_persisted_event(
            message=message,
            client_uuid=client_uuid_raw,
            entry_id=entry_id,
            persisted_status="saved",
        )

        return ProcessResult(
            entry_id=entry_id,
            status="saved",
            detail="Message persisted successfully",
            message_uuid=str(message.uuid),
            created=True,
        )