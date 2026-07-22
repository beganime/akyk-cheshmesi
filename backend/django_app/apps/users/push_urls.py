from django.urls import path

from .push_views import BrowserPushConfigAPIView, BrowserPushSubscriptionAPIView, PushTokenAPIView

urlpatterns = [
    path("push-tokens/", PushTokenAPIView.as_view(), name="push-tokens"),
    path("device-tokens/", PushTokenAPIView.as_view(), name="device-tokens"),
    path("web-push/config/", BrowserPushConfigAPIView.as_view(), name="web-push-config"),
    path("web-push/subscriptions/", BrowserPushSubscriptionAPIView.as_view(), name="web-push-subscriptions"),
]
