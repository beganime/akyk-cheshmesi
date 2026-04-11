from django.urls import path

from .views import AppReleaseListAPIView

urlpatterns = [
    path("app-releases/", AppReleaseListAPIView.as_view(), name="app-releases-list"),
]
