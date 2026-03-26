from django.conf import settings
from django.urls import reverse_lazy

from apps.chats.models import Chat
from apps.complaints.models import Complaint
from apps.knowledge_base.models import KnowledgeBaseArticle, KnowledgeBaseCategory
from apps.mediafiles.models import UploadedMedia
from apps.messaging.models import Message
from apps.stickers.models import StickerPack
from apps.users.models import User


def environment_callback(request):
    if settings.DEBUG:
        return ["Development", "warning"]
    return ["Production", "success"]


def complaints_badge_callback(request):
    return Complaint.objects.filter(status=Complaint.Status.PENDING).count()


def media_pending_badge_callback(request):
    return UploadedMedia.objects.filter(status=UploadedMedia.Status.PENDING).count()


def dashboard_callback(request, context):
    users_count = User.objects.count()
    chats_count = Chat.objects.count()
    messages_count = Message.objects.count()
    complaints_pending = Complaint.objects.filter(status=Complaint.Status.PENDING).count()
    media_count = UploadedMedia.objects.count()
    kb_articles_count = KnowledgeBaseArticle.objects.filter(is_active=True).count()
    kb_categories_count = KnowledgeBaseCategory.objects.filter(is_active=True).count()
    sticker_packs_count = StickerPack.objects.filter(is_active=True).count()

    context.update(
        {
            "dashboard_cards": [
                {
                    "title": "Users",
                    "value": users_count,
                    "link": reverse_lazy("admin:users_user_changelist"),
                    "link_label": "Open users",
                },
                {
                    "title": "Chats",
                    "value": chats_count,
                    "link": reverse_lazy("admin:chats_chat_changelist"),
                    "link_label": "Open chats",
                },
                {
                    "title": "Messages",
                    "value": messages_count,
                    "link": reverse_lazy("admin:messaging_message_changelist"),
                    "link_label": "Open messages",
                },
                {
                    "title": "Pending complaints",
                    "value": complaints_pending,
                    "link": reverse_lazy("admin:complaints_complaint_changelist"),
                    "link_label": "Review complaints",
                },
            ],
            "dashboard_sections": [
                {
                    "title": "Content",
                    "items": [
                        {
                            "title": "Knowledge base articles",
                            "value": kb_articles_count,
                            "link": reverse_lazy("admin:knowledge_base_knowledgebasearticle_changelist"),
                        },
                        {
                            "title": "Knowledge base categories",
                            "value": kb_categories_count,
                            "link": reverse_lazy("admin:knowledge_base_knowledgebasecategory_changelist"),
                        },
                        {
                            "title": "Sticker packs",
                            "value": sticker_packs_count,
                            "link": reverse_lazy("admin:stickers_stickerpack_changelist"),
                        },
                        {
                            "title": "Uploaded media",
                            "value": media_count,
                            "link": reverse_lazy("admin:mediafiles_uploadedmedia_changelist"),
                        },
                    ],
                },
                {
                    "title": "Quick actions",
                    "items": [
                        {
                            "title": "Create article",
                            "value": "New",
                            "link": reverse_lazy("admin:knowledge_base_knowledgebasearticle_add"),
                        },
                        {
                            "title": "Create sticker pack",
                            "value": "New",
                            "link": reverse_lazy("admin:stickers_stickerpack_add"),
                        },
                        {
                            "title": "Open complaints",
                            "value": complaints_pending,
                            "link": reverse_lazy("admin:complaints_complaint_changelist"),
                        },
                        {
                            "title": "Open uploads",
                            "value": media_count,
                            "link": reverse_lazy("admin:mediafiles_uploadedmedia_changelist"),
                        },
                    ],
                },
            ],
        }
    )
    return context