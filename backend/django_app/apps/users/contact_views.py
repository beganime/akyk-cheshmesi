from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response

from apps.chats.models import Chat, ChatMember

from .contact_serializers import UserContactDetailSerializer, UserContactSerializer
from .models import User, UserContact


def sync_contacts_from_chats(user: User) -> None:
    member_chat_ids = ChatMember.objects.filter(user=user, is_active=True).values_list("chat_id", flat=True)
    peers = (
        ChatMember.objects.filter(chat_id__in=member_chat_ids, is_active=True)
        .exclude(user=user)
        .select_related("user")
        .order_by("-updated_at")
    )

    for peer in peers:
        UserContact.objects.update_or_create(
            owner=user,
            contact_user=peer.user,
            defaults={"source": "chat", "last_interaction_at": peer.updated_at},
        )


class ContactListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserContactSerializer

    def get_queryset(self):
        sync_contacts_from_chats(self.request.user)
        return UserContact.objects.filter(owner=self.request.user).select_related("contact_user")


class ContactDetailAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contact_user_uuid = kwargs["user_uuid"]
        contact = get_object_or_404(
            UserContact.objects.select_related("contact_user"),
            owner=request.user,
            contact_user__uuid=contact_user_uuid,
        )
        return Response(UserContactDetailSerializer(contact, context={"request": request}).data, status=200)


class ContactVCardAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contact_user_uuid = kwargs["user_uuid"]
        contact = get_object_or_404(
            UserContact.objects.select_related("contact_user"),
            owner=request.user,
            contact_user__uuid=contact_user_uuid,
        )
        user = contact.contact_user
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "Unknown"

        vcard = "\n".join(
            [
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"FN:{full_name}",
                f"N:{user.last_name or ''};{user.first_name or ''};;;",
                f"EMAIL:{user.email}",
                f"TEL:{user.phone_number}",
                "END:VCARD",
            ]
        )

        response = HttpResponse(vcard, content_type="text/vcard")
        response["Content-Disposition"] = f'attachment; filename="contact-{user.uuid}.vcf"'
        return response
