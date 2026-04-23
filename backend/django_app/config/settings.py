from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    USE_S3=(bool, False),
    EMAIL_USE_SSL=(bool, True),
    EMAIL_USE_TLS=(bool, False),
    EMAIL_TIMEOUT=(int, 10),
    AWS_QUERYSTRING_AUTH=(bool, True),
    AWS_S3_PUBLIC_READ=(bool, False),
    AWS_S3_PRESIGNED_GET_EXPIRES=(int, 3600),
    REDIS_PROFILE_TTL_SECONDS=(int, 86400),
    REDIS_CHAT_TTL_SECONDS=(int, 86400),
    REDIS_HISTORY_LIST_LIMIT=(int, 50),
    REDIS_HISTORY_TTL_SECONDS=(int, 604800),
    REDIS_PRESENCE_TTL_SECONDS=(int, 90),
    MEDIA_MAX_UPLOAD_SIZE_BYTES=(int, 26214400),
    SECURE_COOKIES=(bool, False),
    ENABLE_SECURITY_HEADERS=(bool, True),
    AUTH_EMAILS_ASYNC=(bool, True),
)

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
        "akyl-cheshmesi.ru",
        "www.akyl-cheshmesi.ru",
        "akylcheshmesi.ru",
        "www.akylcheshmesi.ru",
    ],
)

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "storages",
    # Local apps
    "apps.knowledge_base.apps.KnowledgeBaseConfig",
    "apps.common.apps.CommonConfig",
    "apps.users.apps.UsersConfig",
    "apps.chats.apps.ChatsConfig",
    "apps.messaging.apps.MessagingConfig",
    "apps.calls.apps.CallsConfig",
    "apps.mediafiles.apps.MediaFilesConfig",
    "apps.stickers.apps.StickersConfig",
    "apps.complaints.apps.ComplaintsConfig",
    "apps.bots.apps.BotsConfig",
    "apps.releases.apps.ReleasesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.users.middleware.TrackUserActivityMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TASKS_EAGER = env.bool("TASKS_EAGER", default=False)
AUTH_EMAILS_ASYNC = env.bool("AUTH_EMAILS_ASYNC", default=True)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://akyl_user:akyl_password@127.0.0.1:5432/akyl_db",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://127.0.0.1:6379/0"),
        "TIMEOUT": 300,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "var" / "static"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(PROJECT_ROOT / "var" / "media")))
PUBLIC_MEDIA_BASE_URL = env("PUBLIC_MEDIA_BASE_URL", default="").rstrip("/")

MEDIA_MAX_UPLOAD_SIZE_BYTES = env.int("MEDIA_MAX_UPLOAD_SIZE_BYTES", default=26214400)
MEDIA_ALLOWED_CONTENT_TYPES = env.list(
    "MEDIA_ALLOWED_CONTENT_TYPES",
    default=[
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/webm",
        "audio/ogg",
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/zip",
        "application/x-zip-compressed",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    ],
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.common.throttling.BurstScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/hour",
        "auth_register": "10/hour",
        "auth_verify": "20/hour",
        "auth_set_password": "20/hour",
        "auth_login": "20/hour",
        "auth_password_reset": "10/hour",
        "auth_password_reset_confirm": "20/hour",
        "users_me": "120/hour",
        "users_search": "120/hour",
        "complaints": "30/hour",
        "media_list": "120/hour",
        "media_presign": "60/hour",
        "media_complete": "120/hour",
        "media_upload": "30/hour",
        "call_create": "30/hour",
        "call_action": "240/hour",
        "call_history": "240/hour",
    },
}

SIMPLE_JWT = {
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SECRET", default=SECRET_KEY),
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=14)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Akyl Cheshmesi API",
    "DESCRIPTION": "Core backend API for Akyl Cheshmesi messenger",
    "VERSION": "0.1.0",
}

CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://localhost:8081",
        "https://akyl-cheshmesi.ru",
        "https://www.akyl-cheshmesi.ru",
        "https://akylcheshmesi.ru",
        "https://www.akylcheshmesi.ru",
    ],
)

CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://localhost:8081",
        "https://akyl-cheshmesi.ru",
        "https://www.akyl-cheshmesi.ru",
        "https://akylcheshmesi.ru",
        "https://www.akylcheshmesi.ru",
    ],
)

CELERY_BROKER_URL = env("REDIS_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

REDIS_PROFILE_TTL_SECONDS = env.int("REDIS_PROFILE_TTL_SECONDS", default=86400)
REDIS_CHAT_TTL_SECONDS = env.int("REDIS_CHAT_TTL_SECONDS", default=86400)
REDIS_HISTORY_LIST_LIMIT = env.int("REDIS_HISTORY_LIST_LIMIT", default=50)
REDIS_HISTORY_TTL_SECONDS = env.int("REDIS_HISTORY_TTL_SECONDS", default=604800)
REDIS_PRESENCE_TTL_SECONDS = env.int("REDIS_PRESENCE_TTL_SECONDS", default=90)
REDIS_STREAM_MESSAGES_KEY = env("REDIS_STREAM_MESSAGES_KEY", default="stream:messages")

REDIS_STREAM_MESSAGES_GROUP = env("REDIS_STREAM_MESSAGES_GROUP", default="message-savers")
REDIS_STREAM_DLQ_KEY = env("REDIS_STREAM_DLQ_KEY", default="stream:messages:dlq")
REDIS_STREAM_READ_COUNT = env.int("REDIS_STREAM_READ_COUNT", default=20)
REDIS_STREAM_BLOCK_MS = env.int("REDIS_STREAM_BLOCK_MS", default=5000)
REDIS_STREAM_CLAIM_IDLE_MS = env.int("REDIS_STREAM_CLAIM_IDLE_MS", default=60000)

REDIS_STREAM_MESSAGE_STATUS_KEY = env(
    "REDIS_STREAM_MESSAGE_STATUS_KEY",
    default="stream:message-statuses",
)
REDIS_STREAM_MESSAGE_STATUS_GROUP = env(
    "REDIS_STREAM_MESSAGE_STATUS_GROUP",
    default="message-status-savers",
)
REDIS_STREAM_MESSAGE_STATUS_DLQ_KEY = env(
    "REDIS_STREAM_MESSAGE_STATUS_DLQ_KEY",
    default="stream:message-statuses:dlq",
)
REDIS_REALTIME_EVENTS_CHANNEL = env(
    "REDIS_REALTIME_EVENTS_CHANNEL",
    default="realtime:events",
)

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="priem@stud-life.com")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.yandex.ru")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

SECURE_COOKIES = env.bool("SECURE_COOKIES", default=False)
ENABLE_SECURITY_HEADERS = env.bool("ENABLE_SECURITY_HEADERS", default=True)

SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG and ENABLE_SECURITY_HEADERS:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
else:
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_SSL_REDIRECT = False

USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
    AWS_S3_PUBLIC_READ = env.bool("AWS_S3_PUBLIC_READ", default=False)
    AWS_QUERYSTRING_AUTH = env.bool(
        "AWS_QUERYSTRING_AUTH",
        default=not AWS_S3_PUBLIC_READ,
    )
    AWS_S3_PRESIGNED_GET_EXPIRES = env.int("AWS_S3_PRESIGNED_GET_EXPIRES", default=3600)
    AWS_DEFAULT_ACL = "public-read" if AWS_S3_PUBLIC_READ else None
    AWS_S3_FILE_OVERWRITE = False

    aws_s3_verify_raw = env("AWS_S3_VERIFY", default="").strip()
    if aws_s3_verify_raw.lower() in {"false", "0", "no"}:
        AWS_S3_VERIFY = False
    else:
        AWS_S3_VERIFY = aws_s3_verify_raw or None

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "region_name": AWS_S3_REGION_NAME,
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "default_acl": AWS_DEFAULT_ACL,
                "querystring_auth": AWS_QUERYSTRING_AUTH,
                "file_overwrite": AWS_S3_FILE_OVERWRITE,
                "custom_domain": AWS_S3_CUSTOM_DOMAIN or None,
                "verify": AWS_S3_VERIFY,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT,
                "base_url": MEDIA_URL,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

UNFOLD = {
    "SITE_TITLE": "Akyl Cheshmesi Admin",
    "SITE_HEADER": "Akyl Cheshmesi",
    "SITE_SUBHEADER": "Operations & Content",
    "SITE_URL": "/",
    "SITE_SYMBOL": "forum",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": False,
    "ENVIRONMENT": "config.admin_ui.environment_callback",
    "DASHBOARD_CALLBACK": "config.admin_ui.dashboard_callback",
    "BORDER_RADIUS": "10px",
    "SIDEBAR": {
        "show_search": True,
        "command_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Overview"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Messaging"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Chats"),
                        "icon": "forum",
                        "link": reverse_lazy("admin:chats_chat_changelist"),
                    },
                    {
                        "title": _("Messages"),
                        "icon": "chat",
                        "link": reverse_lazy("admin:messaging_message_changelist"),
                    },
                    {
                        "title": _("Bot commands"),
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:bots_botcommand_changelist"),
                    },
                    {
                        "title": _("Calls"),
                        "icon": "call",
                        "link": reverse_lazy("admin:calls_callsession_changelist"),
                    },
                ],
            },
            {
                "title": _("Applications"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Releases"),
                        "icon": "system_update",
                        "link": reverse_lazy("admin:releases_apprelease_changelist"),
                    },
                ],
            },
            {
                "title": _("Content"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Knowledge categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:knowledge_base_knowledgebasecategory_changelist"),
                    },
                    {
                        "title": _("Knowledge articles"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:knowledge_base_knowledgebasearticle_changelist"),
                    },
                    {
                        "title": _("Sticker packs"),
                        "icon": "mood",
                        "link": reverse_lazy("admin:stickers_stickerpack_changelist"),
                    },
                    {
                        "title": _("Uploads"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:mediafiles_uploadedmedia_changelist"),
                        "badge": "config.admin_ui.media_pending_badge_callback",
                        "badge_variant": "warning",
                        "badge_style": "solid",
                    },
                ],
            },
            {
                "title": _("Moderation"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Complaints"),
                        "icon": "report",
                        "link": reverse_lazy("admin:complaints_complaint_changelist"),
                        "badge": "config.admin_ui.complaints_badge_callback",
                        "badge_variant": "danger",
                        "badge_style": "solid",
                    },
                ],
            },
        ],
    },
}