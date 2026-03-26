from django.urls import path

from .views import (
    ChatArchiveAPIView,
    ChatListAPIView,
    ChatMarkReadAPIView,
    ChatMessagesAPIView,
    ChatMuteAPIView,
    ChatPinAPIView,
    ChatRetrieveAPIView,
    DirectChatCreateAPIView,
    GroupChatCreateAPIView,
)

urlpatterns = [
    path("chats/", ChatListAPIView.as_view(), name="chat-list"),
    path("chats/direct/", DirectChatCreateAPIView.as_view(), name="chat-create-direct"),
    path("chats/group/", GroupChatCreateAPIView.as_view(), name="chat-create-group"),
    path("chats/<uuid:chat_uuid>/", ChatRetrieveAPIView.as_view(), name="chat-detail"),
    path("chats/<uuid:chat_uuid>/messages/", ChatMessagesAPIView.as_view(), name="chat-messages"),
    path("chats/<uuid:chat_uuid>/read/", ChatMarkReadAPIView.as_view(), name="chat-read"),
    path("chats/<uuid:chat_uuid>/pin/", ChatPinAPIView.as_view(), name="chat-pin"),
    path("chats/<uuid:chat_uuid>/archive/", ChatArchiveAPIView.as_view(), name="chat-archive"),
    path("chats/<uuid:chat_uuid>/mute/", ChatMuteAPIView.as_view(), name="chat-mute"),
]