from django.urls import path

from .contact_views import ContactDetailAPIView, ContactListAPIView, ContactVCardAPIView
from .presence_views import PresenceBulkAPIView, PresenceDetailAPIView
from .search_views import SearchUsersAPIView
from .views import (
    LoginAPIView,
    MeAPIView,
    PasswordResetAPIView,
    PasswordResetConfirmAPIView,
    RegisterAPIView,
    SetPasswordAPIView,
    TokenRefreshAPIView,
    VerifyEmailAPIView,
)

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
    path("auth/verify-email/", VerifyEmailAPIView.as_view(), name="auth-verify-email"),
    path("auth/set-password/", SetPasswordAPIView.as_view(), name="auth-set-password"),
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshAPIView.as_view(), name="auth-refresh"),
    path("auth/password-reset/", PasswordResetAPIView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmAPIView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("users/me/", MeAPIView.as_view(), name="users-me"),
    path("users/search/", SearchUsersAPIView.as_view(), name="users-search"),
    path("users/contacts/", ContactListAPIView.as_view(), name="users-contacts"),
    path("users/contacts/<uuid:user_uuid>/", ContactDetailAPIView.as_view(), name="users-contacts-detail"),
    path(
        "users/contacts/<uuid:user_uuid>/vcard/",
        ContactVCardAPIView.as_view(),
        name="users-contacts-vcard",
    ),
    path("presence/", PresenceBulkAPIView.as_view(), name="presence-bulk"),
    path("presence/<uuid:user_uuid>/", PresenceDetailAPIView.as_view(), name="presence-detail"),
]
