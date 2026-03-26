from django.urls import path

from .views import ComplaintListCreateAPIView

urlpatterns = [
    path("complaints/", ComplaintListCreateAPIView.as_view(), name="complaints"),
]