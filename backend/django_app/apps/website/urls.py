from django.urls import path

from .views import CompanyTeamListAPIView, PublicSiteContentAPIView, SupportRequestCreateAPIView

urlpatterns = [
    path("website/content/", PublicSiteContentAPIView.as_view(), name="website-content"),
    path("website/team/", CompanyTeamListAPIView.as_view(), name="website-team"),
    path("website/support/", SupportRequestCreateAPIView.as_view(), name="website-support"),
]
