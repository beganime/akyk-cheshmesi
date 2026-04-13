from datetime import timedelta
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OneTimeCode, User
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    UserAuthResponseSerializer,
    UserMeSerializer,
    UserSearchSerializer,
    VerifyEmailSerializer,
)
from .tasks import send_password_reset_email, send_verification_email
from .utils import build_signup_token, generate_otp_code, hash_otp_code, parse_signup_token

OTP_TTL_MINUTES = 10

logger = logging.getLogger(__name__)


class EmailDispatchUnavailable(Exception):
    """Raised when the email task cannot be enqueued."""


def _dispatch_task(task_func, *args):
    """
    В проде письма по регистрации/сбросу пароля не должны отправляться
    синхронно внутри HTTP-запроса, иначе SMTP может повесить gunicorn worker
    и дать 500/502 на фронте.

    Логика:
    - TASKS_EAGER=true  -> выполняем сразу (для локальной отладки/тестов)
    - AUTH_EMAILS_ASYNC=true -> только enqueue в celery
    - AUTH_EMAILS_ASYNC=false -> синхронно, если ты сам этого хочешь
    """
    tasks_eager = bool(getattr(settings, "TASKS_EAGER", False))
    run_async = bool(getattr(settings, "AUTH_EMAILS_ASYNC", True)) and not tasks_eager

    if not run_async:
        return task_func(*args)

    try:
        return task_func.apply_async(
            args=args,
            queue=getattr(settings, "CELERY_TASK_DEFAULT_QUEUE", "default"),
        )
    except Exception as exc:
        logger.exception(
            "Failed to enqueue task %s",
            getattr(task_func, "name", str(task_func)),
        )
        raise EmailDispatchUnavailable("Failed to enqueue email task") from exc


def _issue_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["user_uuid"] = str(user.uuid)
    refresh["email"] = user.email
    refresh["username"] = user.username or ""
    refresh["is_email_verified"] = user.is_email_verified

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _get_active_code(email: str, purpose: str):
    return (
        OneTimeCode.objects.filter(
            email__iexact=email,
            purpose=purpose,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()

        try:
            with transaction.atomic():
                existing_user = User.objects.filter(email__iexact=email).first()

                if existing_user and existing_user.registration_completed:
                    return Response(
                        {"detail": "A user with this email already exists"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if existing_user:
                    user = existing_user
                    user.is_active = False
                    user.is_email_verified = False
                    user.registration_completed = False
                    user.save(
                        update_fields=[
                            "is_active",
                            "is_email_verified",
                            "registration_completed",
                            "updated_at",
                        ]
                    )
                else:
                    user = User.objects.create(
                        email=email,
                        username=None,
                        is_active=False,
                        is_email_verified=False,
                        registration_completed=False,
                    )

                OneTimeCode.objects.filter(
                    email__iexact=email,
                    purpose=OneTimeCode.Purpose.EMAIL_VERIFICATION,
                    used_at__isnull=True,
                ).update(expires_at=timezone.now())

                code = generate_otp_code()

                OneTimeCode.objects.create(
                    user=user,
                    email=email,
                    purpose=OneTimeCode.Purpose.EMAIL_VERIFICATION,
                    code_hash=hash_otp_code(code),
                    expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
                )

                _dispatch_task(send_verification_email, email, code)

        except EmailDispatchUnavailable:
            return Response(
                {
                    "detail": (
                        "Verification email service is temporarily unavailable. "
                        "Please try again in 1-2 minutes."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "detail": "Verification code sent",
                "email": email,
                "expires_in_seconds": OTP_TTL_MINUTES * 60,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_verify"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        otp = _get_active_code(email, OneTimeCode.Purpose.EMAIL_VERIFICATION)
        if not otp:
            return Response(
                {"detail": "Verification code not found or expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp.code_hash != hash_otp_code(code):
            otp.attempts += 1
            otp.save(update_fields=["attempts", "updated_at"])
            return Response(
                {"detail": "Invalid verification code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = otp.user or User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            otp.used_at = timezone.now()
            otp.save(update_fields=["used_at", "updated_at"])

            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])

        verification_token = build_signup_token(str(user.uuid))

        return Response(
            {
                "detail": "Email verified successfully",
                "verification_token": verification_token,
            },
            status=status.HTTP_200_OK,
        )


class SetPasswordAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_set_password"

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = parse_signup_token(serializer.validated_data["verification_token"])
        except Exception:
            return Response(
                {"detail": "Invalid or expired verification token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(uuid=payload.get("user_uuid")).first()
        if not user:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_email_verified:
            return Response(
                {"detail": "Email is not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.registration_completed:
            return Response(
                {"detail": "Registration has already been completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.username = serializer.validated_data["username"]
            user.first_name = serializer.validated_data.get("first_name", user.first_name)
            user.last_name = serializer.validated_data.get("last_name", user.last_name)
            user.date_of_birth = serializer.validated_data.get(
                "date_of_birth",
                user.date_of_birth,
            )
            user.set_password(serializer.validated_data["password"])
            user.is_active = True
            user.registration_completed = True
            user.save()

        tokens = _issue_tokens_for_user(user)
        user_data = UserAuthResponseSerializer(user).data

        return Response(
            {
                "detail": "Password set successfully",
                "tokens": tokens,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            return Response(
                {"detail": "Invalid email or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_email_verified:
            return Response(
                {"detail": "Email is not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.registration_completed or not user.is_active:
            return Response(
                {"detail": "Registration is not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "updated_at"])

        tokens = _issue_tokens_for_user(user)
        user_data = UserAuthResponseSerializer(user).data

        return Response(
            {
                "detail": "Login successful",
                "tokens": tokens,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class PasswordResetAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            return Response(
                {"detail": "If the account exists, reset instructions were sent"},
                status=status.HTTP_200_OK,
            )

        try:
            with transaction.atomic():
                OneTimeCode.objects.filter(
                    email__iexact=email,
                    purpose=OneTimeCode.Purpose.PASSWORD_RESET,
                    used_at__isnull=True,
                ).update(expires_at=timezone.now())

                code = generate_otp_code()

                OneTimeCode.objects.create(
                    user=user,
                    email=email,
                    purpose=OneTimeCode.Purpose.PASSWORD_RESET,
                    code_hash=hash_otp_code(code),
                    expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
                )

                _dispatch_task(send_password_reset_email, email, code)

        except EmailDispatchUnavailable:
            return Response(
                {
                    "detail": (
                        "Password reset email service is temporarily unavailable. "
                        "Please try again in 1-2 minutes."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"detail": "If the account exists, reset instructions were sent"},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        otp = _get_active_code(email, OneTimeCode.Purpose.PASSWORD_RESET)
        if not otp:
            return Response(
                {"detail": "Reset code not found or expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp.code_hash != hash_otp_code(code):
            otp.attempts += 1
            otp.save(update_fields=["attempts", "updated_at"])
            return Response(
                {"detail": "Invalid reset code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = otp.user or User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            otp.used_at = timezone.now()
            otp.save(update_fields=["used_at", "updated_at"])

            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password", "updated_at"])

        return Response(
            {"detail": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_scope = "users_me"

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserMeSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if len(query) < 2:
            return Response(
                {"detail": "Query must contain at least 2 characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = (
            User.objects.filter(
                is_active=True,
                is_email_verified=True,
                registration_completed=True,
            )
            .exclude(id=request.user.id)
            .filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
            .order_by("username")[:20]
        )

        serializer = UserSearchSerializer(users, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)