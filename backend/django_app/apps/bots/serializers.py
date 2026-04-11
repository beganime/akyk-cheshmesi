from rest_framework import serializers

from .models import BotCommand


class BotCommandResolveSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=120)


class BotCommandResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotCommand
        fields = ("command", "response_text")
