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
    MEDIA_SIGNED_URL_TTL_SECONDS=(int, 3600),
    MEDIA_USE_X_ACCEL_REDIRECT=(bool, True),
    MAX_UPLOAD_SIZE_MB=(int, 25),
    IMAGE_MAX_WIDTH=(int, 1920),
    IMAGE_MAX_HEIGHT=(int, 1920),
    IMAGE_THUMBNAIL_SIZE=(int, 480),
    IMAGE_UPLOAD_QUALITY=(int, 82),
    VIDEO_MAX_SIZE_MB=(int, 100),
    VIDEO_NOTE_MAX_SIZE_MB=(int, 50),
    VIDEO_NOTE_MAX_DURATION_SECONDS=(int, 60),
    AUDIO_MAX_SIZE_MB=(int, 25),
    AUDIO_MAX_DURATION_SECONDS=(int, 300),
    STORY_TTL_HOURS=(int, 24),
    SECURE_COOKIES=(bool, False),
    ENABLE_SECURITY_HEADERS=(bool, True),
    AUTH_EMAILS_ASYNC=(bool, True),
    FCM_ENABLED=(bool, False),
    PUSH_NOTIFICATIONS_ASYNC=(bool, True),
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
    "apps.stories.apps.StoriesConfig",
    "apps.mediafiles.apps.MediaFilesConfig",
    "apps.stickers.apps.StickersConfig",
    "apps.complaints.apps.ComplaintsConfig",
    "apps.bots.apps.BotsConfig",
    "apps.releases.apps.ReleasesConfig",
    "apps.website.apps.WebsiteConfig",
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
FCM_ENABLED = env.bool("FCM_ENABLED", default=False)
PUSH_NOTIFICATIONS_ASYNC = env.bool("PUSH_NOTIFICATIONS_ASYNC", default=True)
FCM_PROJECT_ID = env("FCM_PROJECT_ID", default="")
FCM_SERVICE_ACCOUNT_JSON = env("FCM_SERVICE_ACCOUNT_JSON", default="")
FIREBASE_CREDENTIALS_PATH = env(
    "FIREBASE_CREDENTIALS_PATH",
    default=env("FCM_SERVICE_ACCOUNT_FILE", default=""),
)

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
    }
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
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Asia/Ashgabat")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "var" / "static"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(PROJECT_ROOT / "var" / "media")))
PUBLIC_MEDIA_BASE_URL = env("PUBLIC_MEDIA_BASE_URL", default="").rstrip("/")
MEDIA_SIGNED_URL_TTL_SECONDS = env.int("MEDIA_SIGNED_URL_TTL_SECONDS", default=3600)
MEDIA_USE_X_ACCEL_REDIRECT = env.bool("MEDIA_USE_X_ACCEL_REDIRECT", default=True)
MEDIA_X_ACCEL_PREFIX = env("MEDIA_X_ACCEL_PREFIX", default="/_protected_media/")

MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=25)
MEDIA_MAX_UPLOAD_SIZE_BYTES = env.int(
    "MEDIA_MAX_UPLOAD_SIZE_BYTES",
    default=MAX_UPLOAD_SIZE_MB * 1024 * 1024,
)
IMAGE_MAX_WIDTH = env.int("IMAGE_MAX_WIDTH", default=1920)
IMAGE_MAX_HEIGHT = env.int("IMAGE_MAX_HEIGHT", default=1920)
IMAGE_THUMBNAIL_SIZE = env.int("IMAGE_THUMBNAIL_SIZE", default=480)
IMAGE_UPLOAD_QUALITY = env.int("IMAGE_UPLOAD_QUALITY", default=82)
VIDEO_MAX_SIZE_MB = env.int("VIDEO_MAX_SIZE_MB", default=100)
VIDEO_NOTE_MAX_SIZE_MB = env.int("VIDEO_NOTE_MAX_SIZE_MB", default=50)
VIDEO_NOTE_MAX_DURATION_SECONDS = env.int("VIDEO_NOTE_MAX_DURATION_SECONDS", default=60)
AUDIO_MAX_SIZE_MB = env.int("AUDIO_MAX_SIZE_MB", default=25)
AUDIO_MAX_DURATION_SECONDS = env.int("AUDIO_MAX_DURATION_SECONDS", default=300)
STORY_TTL_HOURS = env.int("STORY_TTL_HOURS", default=24)
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
        "audio/aac",
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
MEDIA_ALLOWED_EXTENSIONS = env.list(
    "MEDIA_ALLOWED_EXTENSIONS",
    default=[
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif",
        "mp4",
        "mov",
        "webm",
        "mp3",
        "wav",
        "m4a",
        "aac",
        "ogg",
        "pdf",
        "txt",
        "csv",
        "zip",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
    ],
)
MEDIA_BLOCKED_EXTENSIONS = env.list(
    "MEDIA_BLOCKED_EXTENSIONS",
    default=[
        "php",
        "phtml",
        "phar",
        "asp",
        "aspx",
        "jsp",
        "cgi",
        "pl",
        "py",
        "sh",
        "bash",
        "bat",
        "cmd",
        "ps1",
        "exe",
        "dll",
        "com",
        "scr",
        "msi",
        "jar",
        "html",
        "htm",
        "svg",
        "js",
        "mjs",
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
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
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
        "media_download": "600/hour",
        "call_create": "30/hour",
        "call_action": "240/hour",
        "call_history": "240/hour",
        "stories": "240/hour",
        "stories_create": "60/hour",
        "bots": "120/hour",
        "bot_send_message": "240/hour",
        "website_support": "20/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Akyl Cheshmesi API",
    "DESCRIPTION": "Backend API for Akyl Cheshmesi messenger",
    "VERSION": "1.0.0",
}

UNFOLD = {
    "SITE_TITLE": "Akyl Cheshmesi Admin",
    "SITE_HEADER": "Akyl Cheshmesi",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
}

def _unique_origins(*origin_groups):
    seen = set()
    result = []
    for origins in origin_groups:
        for origin in origins:
            normalized = str(origin).strip().rstrip("/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


CORS_ALLOWED_ORIGINS = _unique_origins(
    env.list("CORS_ALLOWED_ORIGINS", default=[]),
    env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[]),
)

if DEBUG:
    CORS_ALLOWED_ORIGINS = _unique_origins(
        CORS_ALLOWED_ORIGINS,
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://localhost:8082",
            "http://127.0.0.1:8082",
            "http://localhost:19006",
            "http://127.0.0.1:19006",
        ],
    )
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "https://akyl-cheshmesi.ru",
        "https://www.akyl-cheshmesi.ru",
        "https://akylcheshmesi.ru",
        "https://www.akylcheshmesi.ru",
    ],
)

SECURE_COOKIES = env.bool("SECURE_COOKIES", default=False)
ENABLE_SECURITY_HEADERS = env.bool("ENABLE_SECURITY_HEADERS", default=True)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)

if ENABLE_SECURITY_HEADERS:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.mail.ru")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or "noreply@akyl-cheshmesi.ru")


