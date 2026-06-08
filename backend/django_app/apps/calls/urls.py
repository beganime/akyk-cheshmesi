from django.urls import path

from .views import (
    CallAcceptAPIView,
    CallCancelAPIView,
    CallDetailAPIView,
    CallEndAPIView,
    CallHistoryListAPIView,
    CallMissedAPIView,
    CallRejectAPIView,
    CallSignalCreateAPIView,
    ChatCallCreateAPIView,
)

urlpatterns = [
    path("calls/", CallHistoryListAPIView.as_view(), name="call-history"),
    path("calls/<uuid:call_uuid>/", CallDetailAPIView.as_view(), name="call-detail"),
    path("calls/<uuid:call_uuid>/accept/", CallAcceptAPIView.as_view(), name="call-accept"),
    path("calls/<uuid:call_uuid>/decline/", CallRejectAPIView.as_view(), name="call-decline"),
    path("calls/<uuid:call_uuid>/reject/", CallRejectAPIView.as_view(), name="call-reject"),
    path("calls/<uuid:call_uuid>/cancel/", CallCancelAPIView.as_view(), name="call-cancel"),
    path("calls/<uuid:call_uuid>/end/", CallEndAPIView.as_view(), name="call-end"),
    path("calls/<uuid:call_uuid>/missed/", CallMissedAPIView.as_view(), name="call-missed"),
    path("calls/<uuid:call_uuid>/signals/", CallSignalCreateAPIView.as_view(), name="call-signal-create"),
    path("chats/<uuid:chat_uuid>/calls/", ChatCallCreateAPIView.as_view(), name="chat-call-create"),
]
