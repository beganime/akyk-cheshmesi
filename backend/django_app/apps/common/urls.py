from django.urls import path

from .views import healthcheck, readiness

urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("readiness/", readiness, name="readiness"),
]