import logging
import smtplib
import socket

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)


def _send_plain_email(subject: str, message: str, email: str) -> None:
    timeout = int(getattr(settings, "EMAIL_TIMEOUT", 10) or 10)

    connection = get_connection(
        backend=getattr(
            settings,
            "EMAIL_BACKEND",
            "django.core.mail.backends.smtp.EmailBackend",
        ),
        fail_silently=False,
        host=getattr(settings, "EMAIL_HOST", ""),
        port=getattr(settings, "EMAIL_PORT", 0),
        username=getattr(settings, "EMAIL_HOST_USER", "") or None,
        password=getattr(settings, "EMAIL_HOST_PASSWORD", "") or None,
        use_tls=bool(getattr(settings, "EMAIL_USE_TLS", False)),
        use_ssl=bool(getattr(settings, "EMAIL_USE_SSL", False)),
        timeout=timeout,
    )

    try:
        email_message = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            connection=connection,
        )
        sent_count = email_message.send(fail_silently=False)
        if sent_count != 1:
            raise smtplib.SMTPException(
                f"Expected to send 1 email, sent {sent_count}"
            )
    finally:
        try:
            connection.close()
        except Exception:
            logger.exception("Failed to close SMTP connection")


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, socket.timeout, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_verification_email(self, email: str, code: str):
    subject = "Akyl Cheshmesi - email verification code"
    message = (
        "Hello!\n\n"
        f"Your email verification code: {code}\n\n"
        "The code is valid for 10 minutes.\n"
        "If you did not request registration, please ignore this email.\n\n"
        "Akyl Cheshmesi"
    )
    _send_plain_email(subject=subject, message=message, email=email)


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, socket.timeout, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_password_reset_email(self, email: str, code: str):
    subject = "Akyl Cheshmesi - password reset code"
    message = (
        "Hello!\n\n"
        f"Your password reset code: {code}\n\n"
        "The code is valid for 10 minutes.\n"
        "If you did not request a password reset, please ignore this email.\n\n"
        "Akyl Cheshmesi"
    )
    _send_plain_email(subject=subject, message=message, email=email)


@shared_task
def send_push_notification(user_ids: list[int], title: str, body: str, data: dict) -> dict:
    from .push_services import send_push_to_user_ids

    result = send_push_to_user_ids(user_ids, title, body, data)
    logger.info(
        "Push notification task finished | type=%s users=%s attempted=%s sent=%s skipped=%s disabled=%s",
        (data or {}).get("type", ""),
        len(user_ids or []),
        result.attempted_count,
        result.sent_count,
        result.skipped_count,
        result.disabled,
    )
    return result.as_dict()
