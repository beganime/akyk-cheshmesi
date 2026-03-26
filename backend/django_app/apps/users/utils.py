import hashlib
import re
import secrets

from django.conf import settings
from django.core import signing

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.]{4,32}$")


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    raw = f"{settings.SECRET_KEY}:{code}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(username))


def build_signup_token(user_uuid: str) -> str:
    return signing.dumps(
        {"user_uuid": user_uuid, "purpose": "signup"},
        salt="users.signup",
    )


def parse_signup_token(token: str, max_age_seconds: int = 1800) -> dict:
    return signing.loads(
        token,
        salt="users.signup",
        max_age=max_age_seconds,
    )