from django.urls import path

from .push_views import PushTokenAPIView

urlpatterns = [
    path("push-tokens/", PushTokenAPIView.as_view(), name="push-tokens"),
]