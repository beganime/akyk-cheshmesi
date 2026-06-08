# Akyl Cheshmesi Mobile API

Base URLs:

- REST production: `https://akyl-cheshmesi.ru/api/`
- REST compatibility: `https://akyl-cheshmesi.ru/api/v1/`
- WebSocket: `wss://akyl-cheshmesi.ru/ws?token=<access_token>`
- Optional call SFU socket: `wss://akyl-cheshmesi.ru/ws/calls?token=<access_token>`

Authentication uses JWT access/refresh tokens. Send REST auth as `Authorization: Bearer <access_token>`.

## Auth

### Register

`POST /api/auth/register/`

```json
{ "email": "user@example.com" }
```

### Verify Email

`POST /api/auth/verify-email/`

```json
{ "email": "user@example.com", "code": "123456" }
```

### Set Password

`POST /api/auth/set-password/`

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

`POST /api/auth/login/`

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

`POST /api/auth/refresh/`

```json
{ "refresh": "jwt" }
```

### Profile

`GET /api/users/me/`

`PUT /api/users/me/` with JSON or multipart fields.

## Chats

### List

`GET /api/chats/`

Returns only chats where the authenticated user is an active member.

### Create Private Chat

`POST /api/chats/`

```json
{ "type": "private", "peer_uuid": "user-uuid" }
```

Compatibility endpoint: `POST /api/chats/direct/`.

### Create Group Chat

`POST /api/chats/`

```json
{
  "type": "group",
  "title": "Study group",
  "description": "Exam prep",
  "member_uuids": ["user-uuid-1", "user-uuid-2"]
}
```

Compatibility endpoint: `POST /api/chats/group/`.

### Detail / Update / Delete

- `GET /api/chats/{chat_uuid}/`
- `PATCH /api/chats/{chat_uuid}/` group owner/admin only
- `DELETE /api/chats/{chat_uuid}/` group owner only

### Members

- `POST /api/chats/{chat_uuid}/members/`
- `DELETE /api/chats/{chat_uuid}/members/{user_uuid}/`
- `POST /api/chats/{chat_uuid}/admins/`
- `POST /api/chats/{chat_uuid}/leave/`

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
- Owner can assign admins and delete the group.

## Messages

### List

`GET /api/chats/{chat_uuid}/messages/`

Marks undelivered messages as delivered for the current user.

### Send Text

`POST /api/chats/{chat_uuid}/messages/`

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

Supported `message_type` values:

- `text`
- `image`
- `video`
- `file`
- `audio`
- `video_note`
- `sticker`
- `system`

### Reply

```json
{
  "message_type": "text",
  "text": "Answer",
  "reply_to_uuid": "message-uuid",
  "client_uuid": "client-generated-uuid"
}
```

### Edit

`PATCH /api/chats/{chat_uuid}/messages/{message_uuid}/`

```json
{ "text": "Updated text" }
```

Only sender can edit.

### Delete

`DELETE /api/chats/{chat_uuid}/messages/{message_uuid}/`

```json
{ "delete_for": "me" }
```

or:

```json
{ "delete_for": "everyone" }
```

Only sender can delete for everyone.

### Read Receipts

`POST /api/chats/{chat_uuid}/read/`

```json
{ "message_uuid": "last-read-message-uuid" }
```

`message_uuid` is optional. If omitted, all visible messages in the chat are marked read.

## Media

### Local Upload

`POST /api/media/upload-local/` multipart form:

- `file`
- `duration_seconds` optional
- `width` optional
- `height` optional
- `waveform_data` optional JSON list for audio messages

Images are resized/compressed and thumbnails are generated. Videos get a thumbnail if `ffmpeg` is available. Audio metadata can be supplied by the client.

### S3 Presign

`POST /api/media/presign/`

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

`POST /api/media/complete/`

```json
{ "media_uuid": "media-uuid" }
```

### Download URL

`GET /api/media/{media_uuid}/download/`

Limits are configured through env:

- `MAX_UPLOAD_SIZE_MB`
- `IMAGE_MAX_WIDTH`
- `IMAGE_MAX_HEIGHT`
- `VIDEO_MAX_SIZE_MB`
- `VIDEO_NOTE_MAX_SIZE_MB`
- `AUDIO_MAX_SIZE_MB`

## Calls

Media stream is WebRTC. Server stores call status/history and relays signaling.

### Create Call

`POST /api/chats/{chat_uuid}/calls/`

```json
{
  "call_type": "audio",
  "metadata": { "device_id": "ios-1", "device_platform": "ios" }
}
```

`call_type`: `audio` or `video`.

Response includes:

- `uuid`
- `chat_uuid`
- `room_key`
- `status`
- `participants`

### Call Actions

- `POST /api/calls/{call_uuid}/accept/`
- `POST /api/calls/{call_uuid}/decline/`
- `POST /api/calls/{call_uuid}/reject/` compatibility alias
- `POST /api/calls/{call_uuid}/end/`
- `POST /api/calls/{call_uuid}/missed/`
- `POST /api/calls/{call_uuid}/cancel/` initiator only while ringing

Action payload:

```json
{
  "device_id": "ios-1",
  "device_platform": "ios",
  "device_name": "iPhone",
  "metadata": {}
}
```

### Call History

- `GET /api/calls/`
- `GET /api/calls/?chat_uuid={chat_uuid}`
- `GET /api/calls/?status=missed`
- `GET /api/calls/{call_uuid}/`

### REST Signaling Fallback

`POST /api/calls/{call_uuid}/signals/`

```json
{
  "signal_type": "offer",
  "target_user_uuid": "optional-user-uuid",
  "payload": { "sdp": "..." }
}
```

`signal_type`: `invite`, `accept`, `decline`, `end`, `missed`, `offer`, `answer`, `ice-candidate`.

## Stories

Stories are visible for 24 hours and filtered by active chat relationship.

### List

`GET /api/stories/`

### Create

Image/video story:

```json
{
  "media_type": "image",
  "media_uuid": "uploaded-media-uuid",
  "caption": "Hello"
}
```

Text story:

```json
{
  "media_type": "text",
  "caption": "Exam today",
  "background": "#2AABEE"
}
```

### Detail / Delete

- `GET /api/stories/{story_uuid}/`
- `DELETE /api/stories/{story_uuid}/` author only

### Viewers

- `POST /api/stories/{story_uuid}/viewers/` mark story viewed
- `GET /api/stories/{story_uuid}/viewers/` author sees viewers

Cleanup command:

```bash
python manage.py delete_expired_stories
```

## WebSocket

Connect:

```text
wss://akyl-cheshmesi.ru/ws?token=<access_token>
```

Subscribe to chat before sending chat events:

```json
{ "type": "subscribe_chat", "chat_uuid": "chat-uuid" }
```

### Message Events

Client to server:

```json
{
  "type": "message:new",
  "chat_uuid": "chat-uuid",
  "client_uuid": "client-generated-uuid",
  "message_type": "text",
  "text": "Hello"
}
```

Server to clients:

```json
{
  "type": "message:new",
  "chat_uuid": "chat-uuid",
  "payload": {
    "message": {},
    "message_uuid": "message-uuid"
  }
}
```

Other message events:

- `message:edit`
- `message:delete`
- `message:read`
- `message:delivered`

Compatibility event names still accepted:

- `chat_message`
- `message_read`
- `message_delivered`
- `typing_start`
- `typing_stop`
- `call_offer`
- `call_answer`
- `call_ice`

### Typing

```json
{ "type": "typing:start", "chat_uuid": "chat-uuid", "device_id": "ios-1" }
```

```json
{ "type": "typing:stop", "chat_uuid": "chat-uuid", "device_id": "ios-1" }
```

### Presence

```json
{ "type": "user:online", "chat_uuid": "chat-uuid", "device_id": "ios-1" }
```

```json
{ "type": "user:offline", "chat_uuid": "chat-uuid", "device_id": "ios-1" }
```

Presence REST:

- `GET /api/presence/{user_uuid}/`
- `GET /api/presence/?user_uuid={uuid}&user_uuid={uuid2}`

### Calls

Status events:

- `call:invite`
- `call:accept`
- `call:decline`
- `call:end`
- `call:missed`

WebRTC signaling:

```json
{
  "type": "call:offer",
  "chat_uuid": "chat-uuid",
  "call_uuid": "call-uuid",
  "room_key": "room-key",
  "sdp": "..."
}
```

```json
{
  "type": "call:answer",
  "chat_uuid": "chat-uuid",
  "call_uuid": "call-uuid",
  "room_key": "room-key",
  "sdp": "..."
}
```

```json
{
  "type": "call:ice-candidate",
  "chat_uuid": "chat-uuid",
  "call_uuid": "call-uuid",
  "room_key": "room-key",
  "candidate": {
    "candidate": "candidate...",
    "sdpMid": "0",
    "sdpMLineIndex": 0
  }
}
```

Join signaling room:

```json
{
  "type": "join_call",
  "chat_uuid": "chat-uuid",
  "call_uuid": "call-uuid",
  "room_key": "room-key"
}
```

Leave signaling room:

```json
{
  "type": "leave_call",
  "chat_uuid": "chat-uuid",
  "call_uuid": "call-uuid",
  "room_key": "room-key"
}
```
