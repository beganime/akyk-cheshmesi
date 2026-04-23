from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/common/", include("apps.common.urls")),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.users.push_urls")),
    path("api/v1/", include("apps.chats.urls")),
    path("api/v1/", include("apps.calls.urls")),
    path("api/v1/", include("apps.mediafiles.urls")),
    path("api/v1/", include("apps.stickers.urls")),
    path("api/v1/", include("apps.complaints.urls")),
    path("api/v1/", include("apps.knowledge_base.urls")),
    path("api/v1/", include("apps.bots.urls")),
    path("api/v1/", include("apps.releases.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)