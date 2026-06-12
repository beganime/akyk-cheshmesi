# Backend Security Checklist

## Auth And Sessions

- JWT access/refresh tokens are used for API auth.
- Logout can blacklist refresh token and deactivate a device push token.
- Production must use `DJANGO_DEBUG=False`.
- `DJANGO_SECRET_KEY` must come from env and must not be committed.
- Staff access stays in Django admin; public API endpoints require explicit permissions.

## CORS And CSRF

- `DJANGO_CORS_ALLOWED_ORIGINS` must list only trusted web origins.
- `DJANGO_CSRF_TRUSTED_ORIGINS` must list HTTPS production origins.
- Secure cookies and HSTS are enabled in production when security headers are enabled.

## Rate Limits

DRF throttles cover:

- auth login/register/verification/password reset;
- user search;
- chat/message send;
- media presign/upload/download;
- stories and stories create;
- push token registration;
- calls and signaling;
- bots and bot message sending.

Adjust rates in `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` if production telemetry shows abuse or false positives.

## Chat Permissions

- Chat list/detail/messages filter by active `ChatMember`.
- Non-members cannot read or write.
- Removed group members become inactive and lose access to history until re-added.
- Group owner can delete group and manage admins.
- Group admins can manage normal members and group profile.
- Normal members cannot remove users, promote admins, or delete groups.

## Media Security

- S3 is disabled by default; local storage is the primary server storage.
- Uploads are size limited.
- Uploads validate MIME type and extension.
- Dangerous extensions are blocked.
- Physical filenames are generated UUID paths; original names are stored only as metadata.
- Path traversal is rejected before local download.
- Private local file URLs are signed and short lived.
- Nginx direct `/media/` access returns 404 in production.
- Actual file serving uses internal `/_protected_media/` with `X-Accel-Redirect`.
- Media attached to messages or active stories cannot be deleted by users.

## Stories

- Stories are filtered by active chat relationship and `expires_at`.
- Users cannot reply/react to their own story.
- Story replies/reactions create direct chat messages with story metadata.
- Story viewers are visible to the story author.

## Calls And WebSocket

- WebSocket uses access-token authentication.
- Call REST APIs require active chat membership.
- Call signaling payloads include `call_uuid`, `chat_uuid`, `room_key`, `call_type`, `status`, and `initiated_by_uuid`.
- WebRTC media is peer-to-peer; the server stores signaling, status, and logs.
- TURN/STUN credentials must be configured through env, not code.

## Bots

- Bot tokens are never stored in plaintext.
- Raw token is shown only at creation or rotation.
- Bot send API requires `Authorization: Bot <token>`.
- Bot must be an active member of the target chat.
- Bot scopes restrict actions.
- Group bot management is limited to owner/admin.

## Push Notifications

- FCM is disabled by default.
- Missing Firebase credentials must not crash the server.
- Invalid FCM tokens are deactivated after provider errors.
- Message/call push skips muted and archived memberships.
- `.env` and Firebase credentials are ignored by git and must stay out of commits.

## Production Deployment

- Run `python manage.py check --deploy` before release.
- Keep Postgres, Redis, and media volumes backed up.
- Terminate TLS at Nginx.
- Keep `client_max_body_size` aligned with media upload limits.
- Serve static files from Nginx.
- Keep application logs free of secrets, tokens, and stack traces in production responses.
