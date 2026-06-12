# Akyl Cheshmesi Backend Operations

## Local Run

Backend stack:

- Django REST API in `backend/django_app`
- Go realtime WebSocket service in `backend/go-messaging`
- PostgreSQL, Redis, Celery, Nginx in production compose
- Static web cabinet files in `web/`

Local services:

```bash
docker compose -f docker-compose.dev.yml up -d
cd backend/django_app
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open the static web cabinet through Nginx in production at `/messenger/`. For local static-only checks, open `web/messenger.html` or serve the `web/` directory.

## Required Env

Core:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=akyl-cheshmesi.ru,www.akyl-cheshmesi.ru
DJANGO_CORS_ALLOWED_ORIGINS=https://akyl-cheshmesi.ru,https://www.akyl-cheshmesi.ru
DJANGO_CSRF_TRUSTED_ORIGINS=https://akyl-cheshmesi.ru,https://www.akyl-cheshmesi.ru
DATABASE_URL=postgres://akyl_user:password@postgres:5432/akyl_db
REDIS_URL=redis://redis:6379/0
```

Local media storage:

```env
USE_S3=False
MEDIA_ROOT=/app/var/media
MEDIA_URL=/media/
MEDIA_SIGNED_URL_TTL_SECONDS=3600
MEDIA_USE_X_ACCEL_REDIRECT=True
MEDIA_X_ACCEL_PREFIX=/_protected_media/
MAX_UPLOAD_SIZE_MB=25
IMAGE_MAX_WIDTH=1600
IMAGE_MAX_HEIGHT=1600
VIDEO_MAX_SIZE_MB=100
VIDEO_NOTE_MAX_SIZE_MB=25
AUDIO_MAX_SIZE_MB=25
MEDIA_ALLOWED_EXTENSIONS=jpg,jpeg,png,webp,gif,mp4,mov,webm,mp3,wav,m4a,aac,ogg,pdf,txt,csv,zip,doc,docx,xls,xlsx,ppt,pptx
MEDIA_BLOCKED_EXTENSIONS=php,phtml,phar,asp,aspx,jsp,cgi,pl,py,sh,bash,bat,cmd,ps1,exe,dll,com,scr,msi,jar,html,htm,svg,js,mjs
```

Push:

```env
FCM_ENABLED=False
FCM_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase-service-account.json
```

Never commit `.env`, Firebase service-account JSON, private keys, or production database dumps.

## Local Media Flow

1. Client uploads multipart data to `POST /api/media/upload-local/`.
2. Django validates size, MIME type, extension, and media kind.
3. Django stores the file under a generated safe path in `MEDIA_ROOT/uploads/{user_uuid}/`.
4. The database stores `UploadedMedia` with owner, original filename, content type, size, metadata, and thumbnail path.
5. Messages attach media by UUID through `attachment_uuids`.
6. API serializers return signed `file_url` and `thumbnail_url`.
7. In production, Django validates the signed URL or authenticated permission and returns `X-Accel-Redirect`.
8. Nginx serves the file from internal `/_protected_media/`; direct `/media/` access returns 404.

Private media access is allowed only to:

- staff users;
- the media owner;
- active members of a chat containing a message attachment;
- users who can see the story that uses the media;
- anyone if the media object is explicitly public.

## Groups

Rules:

- active members can read/send messages;
- owner can update/delete group, add/remove members, assign/remove admins, and manage bots;
- admins can update group info and add/remove normal members;
- normal members cannot manage other members;
- removed members are set inactive and lose access to the chat and history until re-added.

Key endpoints:

- `GET /api/chats/`
- `POST /api/chats/`
- `PATCH /api/chats/{chat_uuid}/`
- `DELETE /api/chats/{chat_uuid}/`
- `POST /api/chats/{chat_uuid}/members/`
- `DELETE /api/chats/{chat_uuid}/members/{user_uuid}/`
- `POST /api/chats/{chat_uuid}/admins/`
- `DELETE /api/chats/{chat_uuid}/admins/{user_uuid}/`
- `POST /api/chats/{chat_uuid}/leave/`

## Bots

Bots are service users owned by a real user.

Security rules:

- bot tokens are hashed in the database;
- raw token is returned only during bot creation or token rotation;
- bot must be an active member of the chat;
- bot scopes are checked before bot actions;
- direct chat members and group owner/admin can manage bot membership.

Key endpoints:

- `GET /api/bots/`
- `POST /api/bots/`
- `GET /api/bots/{bot_uuid}/`
- `PATCH /api/bots/{bot_uuid}/`
- `DELETE /api/bots/{bot_uuid}/`
- `POST /api/bots/{bot_uuid}/rotate-token/`
- `GET /api/chats/{chat_uuid}/bots/`
- `POST /api/chats/{chat_uuid}/bots/`
- `DELETE /api/chats/{chat_uuid}/bots/{bot_uuid}/`
- `POST /api/bots/send-message/` with `Authorization: Bot <token>`

Supported scopes:

- `send_message`
- `read_messages`
- `upload_media`
- `manage_chat`

## Production Nginx

Production media must be served through the internal location:

```nginx
location /media/ {
    return 404;
}

location /_protected_media/ {
    internal;
    alias /var/www/media/;
    access_log off;
    expires 1h;
    add_header Accept-Ranges bytes;
}
```

This prevents direct path guessing and lets Nginx handle file streaming after Django validates access.

## Checks

From `backend/django_app`:

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py check
python manage.py test
```

Docker config:

```bash
docker compose --env-file env/.env.prod.example -f docker-compose.prod.yml config --quiet
```

Frontend static syntax can be checked from the repository root with:

```bash
node --check web/app.js
```

## Remaining Integration Work

- run production FCM with a real Firebase project and service account;
- add APNS direct provider if iOS will not use Firebase Messaging;
- add outbound bot webhooks if integrations need callbacks;
- move heavy video transcoding to Celery if upload volume grows;
- add admin analytics for media and bot usage.
