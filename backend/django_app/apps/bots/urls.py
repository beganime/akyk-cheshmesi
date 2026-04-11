from django.urls import path

from .views import BotCommandResolveAPIView

urlpatterns = [
    path("bots/resolve-command/", BotCommandResolveAPIView.as_view(), name="bots-resolve-command"),
]
