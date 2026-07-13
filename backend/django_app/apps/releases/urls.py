from django.urls import path

from .views import AppReleaseListAPIView, app_release_download

urlpatterns = [
    path("app-releases/", AppReleaseListAPIView.as_view(), name="app-releases-list"),
    path("app-releases/<uuid:release_uuid>/download/", app_release_download, name="app-release-download"),
]
