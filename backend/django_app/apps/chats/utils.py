def build_direct_chat_key(user_a_uuid: str, user_b_uuid: str) -> str:
    pair = sorted([str(user_a_uuid), str(user_b_uuid)])
    return f"{pair[0]}:{pair[1]}"


def get_or_create_direct_chat_between(current_user, peer_user):
    from django.db import transaction

    from apps.chats.models import Chat, ChatMember

    direct_key = build_direct_chat_key(current_user.uuid, peer_user.uuid)

    with transaction.atomic():
        chat = Chat.objects.select_for_update().filter(direct_key=direct_key).first()
        if not chat:
            chat = Chat.objects.create(
                chat_type=Chat.ChatType.DIRECT,
                direct_key=direct_key,
                creator=current_user,
                members_count=2,
                is_active=True,
            )

        ChatMember.objects.update_or_create(
            chat=chat,
            user=current_user,
            defaults={
                "role": ChatMember.Role.OWNER,
                "is_active": True,
                "can_send_messages": True,
            },
        )
        ChatMember.objects.update_or_create(
            chat=chat,
            user=peer_user,
            defaults={
                "role": ChatMember.Role.MEMBER,
                "is_active": True,
                "can_send_messages": True,
            },
        )

        active_members_count = chat.members.filter(is_active=True).count()
        if chat.members_count != active_members_count or not chat.is_active:
            chat.members_count = active_members_count
            chat.is_active = True
            chat.save(update_fields=["members_count", "is_active", "updated_at"])

    return chat
