from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions

from .public_serializers import UserShortSerializer

User = get_user_model()


class SearchUsersAPIView(generics.ListAPIView):
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "users_search"

    def get_queryset(self):
        query = (self.request.query_params.get("q") or "").strip()

        if not query:
            return User.objects.none()

        return (
            User.objects.filter(
                is_active=True,
                is_email_verified=True,
                registration_completed=True,
            )
            .exclude(id=self.request.user.id)
            .filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
            .order_by("username", "first_name", "last_name")
        )