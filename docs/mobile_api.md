# Akyl Cheshmesi Mobile API

Base URLs:

- REST production: `https://akyl-cheshmesi.ru/api/v1/`
- REST legacy compatibility: `https://akyl-cheshmesi.ru/api/`
- WebSocket: `wss://akyl-cheshmesi.ru/ws?token=<access_token>`
- Optional call SFU socket: `wss://akyl-cheshmesi.ru/ws/calls?token=<access_token>`

Authentication uses JWT access/refresh tokens. Send REST auth as `Authorization: Bearer <access_token>`.

## Auth

### Register

`POST /api/v1/auth/register/`

```json
{ "email": "user@example.com" }
```

### Verify Email

`POST /api/v1/auth/verify-email/`

```json
{ "email": "user@example.com", "code": "123456" }
```

### Set Password

`POST /api/v1/auth/set-password/`

```json
{
  "verification_token": "token",
  "username": "begenc",
  "password": "strong-password",
  "password_confirm": "strong-password",
  "first_name": "Begenc",
  "last_name": "Yagmyrov"
}
```

### Login

`POST /api/v1/auth/login/`

```json
{ "email": "user@example.com", "password": "strong-password" }
```

Response includes:

```json
{
  "tokens": { "access": "jwt", "refresh": "jwt" },
  "user": { "uuid": "..." }
}
```

### Refresh

`POST /api/v1/auth/refresh/`

```json
{ "refresh": "jwt" }
```

### Logout

`POST /api/v1/auth/logout/`

```json
{ "refresh": "jwt" }
```

### Profile

- `GET /api/v1/users/me/`
- `PUT /api/v1/users/me/` JSON or multipart

## Chats

### List

`GET /api/v1/chats/`

Returns only chats where the authenticated user is an active member.

### Create Private Chat

`POST /api/v1/chats/`

```json
{ "type": "private", "peer_uuid": "user-uuid" }
```

Compatibility endpoint: `POST /api/v1/chats/direct/`.

### Messages

- `GET /api/v1/chats/{chat_uuid}/messages/`
- `POST /api/v1/chats/{chat_uuid}/messages/`

### Create Group Chat

`POST /api/v1/chats/`

```json
{
  "type": "group",
  "title": "Study group",
  "description": "Exam prep",
  "member_uuids": ["user-uuid-1", "user-uuid-2"]
}
```

Compatibility endpoint: `POST /api/v1/chats/group/`.

### Detail / Update / Delete

- `GET /api/v1/chats/{chat_uuid}/`
- `PATCH /api/v1/chats/{chat_uuid}/` group owner/admin only
- `DELETE /api/v1/chats/{chat_uuid}/` group owner only

### Members

- `POST /api/v1/chats/{chat_uuid}/members/`
- `DELETE /api/v1/chats/{chat_uuid}/members/{user_uuid}/`
- `POST /api/v1/chats/{chat_uuid}/admins/`
- `DELETE /api/v1/chats/{chat_uuid}/admins/{user_uuid}/`
- `POST /api/v1/chats/{chat_uuid}/leave/`

Add/promote payload:

```json
{ "member_uuids": ["user-uuid"] }
```

or:

```json
{ "user_uuid": "user-uuid" }
```

Permissions:

- Non-members cannot read or write.
- Members can send messages.
- Admins can update group info and add/remove normal members.
- Owner can assign/remove admins and delete the group.
- Removed members lose access to the chat and message history until they are added again.

## Messages

### List

`GET /api/v1/chats/{chat_uuid}/messages/`

Marks undelivered messages as delivered for the current user.

### Send Text

`POST /api/v1/chats/{chat_uuid}/messages/`

```json
{
  "message_type": "text",
  "text": "Hello",
  "client_uuid": "client-generated-uuid"
}
```

### Send Media

Upload media first, then send message with `attachment_uuids`.

```json
{
  "message_type": "image",
  "attachment_uuids": ["media-uuid"],
  "client_uuid": "client-generated-uuid"
}
```

Supported message types: `text`, `image`, `video`, `file`, `audio`, `video_note`, `sticker`, `system`.

## Push Notifications

Register the device token after login and refresh it whenever Firebase/APNS rotates the token.

- `POST /api/v1/push-tokens/`
- `DELETE /api/v1/push-tokens/`
- Compatibility alias: `POST /api/v1/device-tokens/`, `DELETE /api/v1/device-tokens/`

Register payload:

```json
{
  "token": "provider-token",
  "provider": "fcm",
  "platform": "android",
  "device_id": "stable-device-id",
  "device_name": "Pixel",
  "app_version": "1.0.0",
  "meta": { "locale": "ru" }
}
```

Allowed values:

- `provider`: `fcm`, `apns`
- `platform`: `android`, `ios`, `web`

Delete on logout:

```json
{ "token": "provider-token" }
```

or:

```json
{ "provider": "fcm", "platform": "android", "device_id": "stable-device-id" }
```

### Android Channels

The mobile app must create these notification channels before receiving push:

- `calls` for incoming/missed calls
- `messages` for chat messages

Backend sets both `data.channel_id` and `android.notification.channel_id`. Incoming calls use Android `high` priority and `ttl=60s`. Message pushes also use `high` priority.

### Message Push Data

FCM/APNS payload always includes visible `notification` title/body and the full `data` object. Mobile must route by `data.type`.

```json
{
  "type": "message",
  "channel_id": "messages",
  "chat_uuid": "chat-uuid",
  "message_uuid": "message-uuid",
  "sender_uuid": "sender-user-uuid",
  "sender_name": "Sender Name",
  "message_type": "text",
  "preview": "Message preview"
}
```

Tap behavior: open `chat_uuid` and scroll/highlight `message_uuid` when possible.

### Incoming Call Push Data

```json
{
  "type": "call",
  "event": "incoming_call",
  "channel_id": "calls",
  "call_uuid": "call-uuid",
  "chat_uuid": "chat-uuid",
  "room_key": "call-room-key",
  "call_type": "audio",
  "status": "ringing",
  "initiated_by_uuid": "caller-user-uuid",
  "caller_uuid": "caller-user-uuid",
  "caller_name": "Caller Name"
}
```

Incoming call pushes are short-lived. Android FCM uses `android.ttl=60s`; APNS direct sends `apns-expiration` approximately 60 seconds in the future when configured.

### Missed Call Push Data

```json
{
  "type": "missed_call",
  "event": "missed_call",
  "channel_id": "calls",
  "call_uuid": "call-uuid",
  "chat_uuid": "chat-uuid",
  "room_key": "call-room-key",
  "call_type": "audio",
  "status": "missed",
  "initiated_by_uuid": "caller-user-uuid",
  "caller_uuid": "caller-user-uuid",
  "caller_name": "Caller Name"
}
```

If the app is foreground, it should use push data or WebSocket `call:invite` to open the incoming call screen. If background/closed, tapping the push should open the same call screen using `call_uuid` and `room_key`.

## Media

Mobile must not build `/media/...` URLs manually. Use `file_url` and `thumbnail_url` from backend responses.

### Local multipart upload

`POST /api/v1/media/upload-local/`

Content-Type: `multipart/form-data`

Supported fields:

| Field | Required | Notes |
|---|---:|---|
| `file` | yes | Binary file. |
| `is_public` | no | Boolean. Multipart strings like `"false"`, `"0"`, `"true"`, `"1"` are accepted. |
| `width` | no | Integer. Multipart strings are accepted. |
| `height` | no | Integer. Multipart strings are accepted. |
| `duration_seconds` | no | Integer, useful for video/audio. Multipart strings are accepted. |
| `media_kind` | no | Optional client hint: `image`, `video`, `audio`, `file`. If sent, it must match the detected file type. |
| `mime_type` | no | Optional content type override, for example `image/jpeg` or `video/mp4`. |
| `content_type` | no | Alias for `mime_type`. |
| `original_name` | no | Optional original filename override. |
| `waveform_data` | no | JSON list for audio messages, for example `[8, 18, 31]`. |

Example image upload:

```http
POST /api/v1/media/upload-local/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<binary>
is_public=false
width=750
height=429
mime_type=image/jpeg
original_name=story-image.jpg
```

Example video upload:

```http
POST /api/v1/media/upload-local/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<binary>
is_public=false
width=750
height=429
duration_seconds=12
media_kind=video
mime_type=video/mp4
original_name=story-video.mp4
```

Success response: `201 Created`.

```json
{
  "uuid": "uploaded-media-uuid",
  "media_kind": "image",
  "content_type": "image/jpeg",
  "original_name": "story-image.jpg",
  "file_url": "https://akyl-cheshmesi.ru/media/uploads/.../story-image.jpg",
  "thumbnail_url": "https://akyl-cheshmesi.ru/media/uploads/.../story-image-thumb.webp",
  "width": 750,
  "height": 429,
  "duration_seconds": null,
  "size": 123456,
  "size_bytes": 123456,
  "is_public": false,
  "status": "uploaded"
}
```

Invalid uploads return `400` JSON, not `500`:

```json
{ "detail": "Unsupported content type: application/x-unknown" }
```

or serializer errors:

```json
{ "file": ["No file was submitted."] }
```

### S3 Presign

`POST /api/v1/media/presign/`

Use this only when `USE_S3=True` and mobile is doing direct-to-S3 upload.

```json
{
  "filename": "voice.ogg",
  "content_type": "audio/ogg",
  "size": 123456,
  "duration_seconds": 12,
  "waveform_data": [8, 18, 31, 15]
}
```

Complete S3 upload:

`POST /api/v1/media/complete/`

```json
{ "media_uuid": "media-uuid" }
```

### Download URL

`GET /api/v1/media/{media_uuid}/download/`

```json
{ "download_url": "https://..." }
```

Serializers return `file_url` and `thumbnail_url` as short-lived signed API URLs for local private media. Production Nginx serves the actual file through an internal `/_protected_media/` alias after Django validates the signed URL or authenticated permissions.

### Media Detail / Delete

- `GET /api/media/{media_uuid}/`
- `DELETE /api/media/{media_uuid}/`

Only the media owner or staff can delete a media object. Media attached to messages or active stories is protected from deletion to avoid broken chat history.

Limits are configured through env:

- `MEDIA_MAX_UPLOAD_SIZE_BYTES`
- `MAX_UPLOAD_SIZE_MB`
- `IMAGE_MAX_WIDTH`
- `IMAGE_MAX_HEIGHT`
- `VIDEO_MAX_SIZE_MB`
- `VIDEO_NOTE_MAX_SIZE_MB`
- `AUDIO_MAX_SIZE_MB`
- `MEDIA_SIGNED_URL_TTL_SECONDS`
- `MEDIA_ALLOWED_EXTENSIONS`
- `MEDIA_BLOCKED_EXTENSIONS`

## Bots

Bots are Telegram-like service accounts owned by a user. Bot tokens are stored hashed and returned only on create or token rotation.

Scopes:

- `send_message`
- `read_messages`
- `upload_media`
- `manage_chat`

### My Bots

`GET /api/bots/`

`POST /api/bots/`

```json
{
  "username": "helper_bot",
  "title": "Helper Bot",
  "description": "Answers in study groups",
  "scopes": ["send_message"],
  "webhook_url": ""
}
```

Create response includes one-time `token`:

```json
{
  "uuid": "bot-uuid",
  "username": "helper_bot",
  "title": "Helper Bot",
  "token": "bot_..."
}
```

### Bot Detail

- `GET /api/bots/{bot_uuid}/`
- `PATCH /api/bots/{bot_uuid}/`
- `DELETE /api/bots/{bot_uuid}/`
- `POST /api/bots/{bot_uuid}/rotate-token/`

### Bot Chat Membership

- `GET /api/chats/{chat_uuid}/bots/`
- `POST /api/chats/{chat_uuid}/bots/`
- `DELETE /api/chats/{chat_uuid}/bots/{bot_uuid}/`

Add bot payload:

```json
{
  "bot_uuid": "bot-uuid",
  "scopes": ["send_message"]
}
```

Only a direct chat member or group owner/admin can manage bot membership. A bot is also added as an active chat member so normal message permissions still apply.

### Send Bot Message

`POST /api/bots/send-message/`

Header:

```text
Authorization: Bot bot_...
```

Payload:

```json
{
  "chat_uuid": "chat-uuid",
  "text": "Hello from bot",
  "metadata": { "source": "integration" }
}
```

Response is the created message object. Webhook URLs are stored on the bot profile for integration metadata; outbound webhook delivery is left for a later integration sprint.

## Stories

Stories are visible for 24 hours and filtered by active chat relationship. Mobile should upload media first, then create story with `media_uuid`.

### List

`GET /api/v1/stories/`

Response:

```json
{
  "results": [
    {
      "uuid": "story-uuid",
      "media_type": "image",
      "caption": "optional",
      "media": {
        "uuid": "uploaded-media-uuid",
        "media_kind": "image",
        "content_type": "image/jpeg",
        "file_url": "https://...",
        "thumbnail_url": "https://...",
        "width": 750,
        "height": 429,
        "size_bytes": 123456
      }
    }
  ]
}
```

### Create image/video story

`POST /api/v1/stories/`

Image:

```json
{
  "media_type": "image",
  "media_uuid": "uploaded-media-uuid",
  "caption": "optional"
}
```

Video:

```json
{
  "media_type": "video",
  "media_uuid": "uploaded-media-uuid",
  "caption": "optional"
}
```

The backend accepts `media_uuid`. It does not require raw file upload on `/api/v1/stories/`.

Validation rules:

- `media_type=image` requires an uploaded media object with `media_kind=image`.
- `media_type=video` requires an uploaded media object with `media_kind=video`.
- Media must belong to the authenticated user.
- Media must have status `uploaded`.

### Create text story

`POST /api/v1/stories/`

```json
{
  "media_type": "text",
  "caption": "Exam today",
  "background": "#2AABEE"
}
```

### Detail / Delete

- `GET /api/v1/stories/{story_uuid}/`
- `DELETE /api/v1/stories/{story_uuid}/` author only

Detail returns the same `media.file_url` and `media.thumbnail_url` contract as list.

### Viewers

- `POST /api/v1/stories/{story_uuid}/viewers/` mark story viewed
- `GET /api/v1/stories/{story_uuid}/viewers/` author sees viewers

### Reply

`POST /api/v1/stories/{story_uuid}/reply/`

```json
{ "text": "Nice story" }
```

### React

`POST /api/v1/stories/{story_uuid}/react/`

```json
{ "emoji": "🔥" }
```

Cleanup command:

```bash
python manage.py delete_expired_stories
```

## Calls

Media stream is WebRTC. Server stores call status/history and relays signaling.

- `POST /api/v1/chats/{chat_uuid}/calls/`
- `POST /api/v1/calls/{call_uuid}/accept/`
- `POST /api/v1/calls/{call_uuid}/decline/`
- `POST /api/v1/calls/{call_uuid}/end/`
- `POST /api/v1/calls/{call_uuid}/missed/`
- `POST /api/v1/calls/{call_uuid}/cancel/`
- `GET /api/v1/calls/`
- `GET /api/v1/calls/{call_uuid}/`

Call lifecycle:

- Creating a call creates a `CallSession` and participants regardless of recipient online/offline status.
- `call:invite` is published to the chat realtime channel and an incoming call push is sent to recipients.
- `call:accept` marks the participant joined and the session accepted. It does not end the call.
- `call:decline`, `call:end`, `call:missed`, and `call:cancel` move the relevant participant/session toward a final state.
- Pending/ringing calls expire after `CALL_PENDING_TIMEOUT_SECONDS` (default `60`) and become `missed`.
- Accepted calls expire after `CALL_MAX_DURATION_SECONDS` (default `3600`) to prevent permanently active calls.
- Expired ringing calls publish `call:auto-end` and send `missed_call` push.

Supported realtime call events/signals:

- `call:invite`
- `call:accept`
- `call:decline`
- `call:end`
- `call:missed`
- `call:offer`
- `call:answer`
- `call:ice-candidate`

The backend also provides `python manage.py expire_stale_calls`; run it every minute in production if you want stale calls closed without waiting for the next call/list/detail API request.

## WebSocket

Connect:

```text
wss://akyl-cheshmesi.ru/ws?token=<access_token>
```

Subscribe to chat before sending chat events:

```json
{ "type": "subscribe_chat", "chat_uuid": "chat-uuid" }
```
