from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_verification_email(self, email: str, code: str):
    subject = "Akyl Cheshmesi — код подтверждения email"
    message = (
        "Здравствуйте!\n\n"
        f"Ваш код подтверждения: {code}\n\n"
        "Код действует 10 минут.\n"
        "Если вы не запрашивали регистрацию, просто проигнорируйте это письмо.\n\n"
        "Akyl Cheshmesi"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email(self, email: str, code: str):
    subject = "Akyl Cheshmesi — код сброса пароля"
    message = (
        "Здравствуйте!\n\n"
        f"Ваш код сброса пароля: {code}\n\n"
        "Код действует 10 минут.\n"
        "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.\n\n"
        "Akyl Cheshmesi"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )