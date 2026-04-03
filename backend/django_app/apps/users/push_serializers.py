from django.utils import timezone
from rest_framework import serializers

from .models import DevicePushToken


class PushTokenUpsertSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    provider = serializers.ChoiceField(choices=DevicePushToken.Provider.choices)
    platform = serializers.ChoiceField(choices=DevicePushToken.Platform.choices)
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=128)
    device_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    app_version = serializers.CharField(required=False, allow_blank=True, max_length=40)
    meta = serializers.JSONField(required=False)

    def save(self, **kwargs):
        user = self.context["request"].user
        validated = self.validated_data

        token_value = validated["token"].strip()
        provider = validated["provider"]
        platform = validated["platform"]
        device_id = (validated.get("device_id") or "").strip()

        push_token, created = DevicePushToken.objects.get_or_create(
            token=token_value,
            defaults={
                "user": user,
                "provider": provider,
                "platform": platform,
                "device_id": device_id,
                "device_name": (validated.get("device_name") or "").strip(),
                "app_version": (validated.get("app_version") or "").strip(),
                "is_active": True,
                "last_seen_at": timezone.now(),
                "meta": validated.get("meta") or {},
            },
        )

        if not created:
            push_token.user = user
            push_token.provider = provider
            push_token.platform = platform
            push_token.device_id = device_id
            push_token.device_name = (validated.get("device_name") or "").strip()
            push_token.app_version = (validated.get("app_version") or "").strip()
            push_token.is_active = True
            push_token.last_seen_at = timezone.now()
            push_token.meta = validated.get("meta") or {}
            push_token.save()

        if device_id:
            DevicePushToken.objects.filter(
                user=user,
                provider=provider,
                platform=platform,
                device_id=device_id,
                is_active=True,
            ).exclude(id=push_token.id).update(is_active=False)

        return push_token


class PushTokenDeleteSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, allow_blank=True, max_length=512)
    provider = serializers.ChoiceField(
        required=False,
        choices=DevicePushToken.Provider.choices,
    )
    platform = serializers.ChoiceField(
        required=False,
        choices=DevicePushToken.Platform.choices,
    )
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate(self, attrs):
        token = (attrs.get("token") or "").strip()
        provider = attrs.get("provider")
        platform = attrs.get("platform")
        device_id = (attrs.get("device_id") or "").strip()

        if token:
            attrs["token"] = token
            return attrs

        if not (provider and platform and device_id):
            raise serializers.ValidationError(
                "Provide either token, or provider + platform + device_id"
            )

        attrs["device_id"] = device_id
        return attrs

    def deactivate(self):
        user = self.context["request"].user
        validated = self.validated_data

        queryset = DevicePushToken.objects.filter(user=user, is_active=True)

        if validated.get("token"):
            queryset = queryset.filter(token=validated["token"])
        else:
            queryset = queryset.filter(
                provider=validated["provider"],
                platform=validated["platform"],
                device_id=validated["device_id"],
            )

        updated = queryset.update(is_active=False, last_seen_at=timezone.now())
        return updated