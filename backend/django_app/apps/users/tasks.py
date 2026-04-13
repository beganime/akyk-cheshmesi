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
    subject = "Akyl Cheshmesi — код подтверждения email"
    message = (
        "Здравствуйте!\n\n"
        f"Ваш код подтверждения: {code}\n\n"
        "Код действует 10 минут.\n"
        "Если вы не запрашивали регистрацию, просто проигнорируйте это письмо.\n\n"
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
    subject = "Akyl Cheshmesi — код сброса пароля"
    message = (
        "Здравствуйте!\n\n"
        f"Ваш код сброса пароля: {code}\n\n"
        "Код действует 10 минут.\n"
        "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.\n\n"
        "Akyl Cheshmesi"
    )
    _send_plain_email(subject=subject, message=message, email=email)