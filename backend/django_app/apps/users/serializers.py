from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User
from .utils import is_valid_username


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class SetPasswordSerializer(serializers.Serializer):
    verification_token = serializers.CharField()
    username = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate_username(self, value: str) -> str:
        username = value.strip()

        if not is_valid_username(username):
            raise serializers.ValidationError(
                "Username must be 4-32 chars and contain only letters, digits, _ or ."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("This username is already taken")

        return username.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})

        validate_password(attrs["password"])
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match"}
            )

        validate_password(attrs["new_password"])
        return attrs


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "uuid",
            "email",
            "username",
            "first_name",
            "last_name",
            "date_of_birth",
            "avatar",
            "bio",
            "is_email_verified",
            "registration_completed",
        )
        read_only_fields = (
            "uuid",
            "email",
            "username",
            "is_email_verified",
            "registration_completed",
        )


class UserAuthResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "uuid",
            "email",
            "username",
            "first_name",
            "last_name",
            "date_of_birth",
            "avatar",
            "bio",
            "is_email_verified",
            "registration_completed",
        )


class UserSearchSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "uuid",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "avatar",
            "bio",
        )

    def get_full_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name