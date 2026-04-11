from django.urls import path

from .views import (
    LocalMediaUploadAPIView,
    MediaDownloadAPIView,
    MediaCompleteAPIView,
    MediaPresignAPIView,
    MyUploadedMediaListAPIView,
)

urlpatterns = [
    path("media/my/", MyUploadedMediaListAPIView.as_view(), name="media-my"),
    path("media/presign/", MediaPresignAPIView.as_view(), name="media-presign"),
    path("media/complete/", MediaCompleteAPIView.as_view(), name="media-complete"),
    path("media/upload-local/", LocalMediaUploadAPIView.as_view(), name="media-upload-local"),
    path("media/<uuid:media_uuid>/download/", MediaDownloadAPIView.as_view(), name="media-download"),
]
