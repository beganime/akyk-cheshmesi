from django.urls import path

from .views import (
    BotCommandResolveAPIView,
    BotDetailAPIView,
    BotListCreateAPIView,
    BotRotateTokenAPIView,
    BotSendMessageAPIView,
    ChatBotDetailAPIView,
    ChatBotListCreateAPIView,
)

urlpatterns = [
    path("bots/", BotListCreateAPIView.as_view(), name="bots-list"),
    path("bots/send-message/", BotSendMessageAPIView.as_view(), name="bots-send-message"),
    path("bots/<uuid:bot_uuid>/", BotDetailAPIView.as_view(), name="bots-detail"),
    path("bots/<uuid:bot_uuid>/rotate-token/", BotRotateTokenAPIView.as_view(), name="bots-rotate-token"),
    path("bots/resolve-command/", BotCommandResolveAPIView.as_view(), name="bots-resolve-command"),
    path("chats/<uuid:chat_uuid>/bots/", ChatBotListCreateAPIView.as_view(), name="chat-bots"),
    path("chats/<uuid:chat_uuid>/bots/<uuid:bot_uuid>/", ChatBotDetailAPIView.as_view(), name="chat-bots-detail"),
]
