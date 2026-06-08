from django.urls import path

from .views import StoryDetailAPIView, StoryListCreateAPIView, StoryViewersAPIView

urlpatterns = [
    path("stories/", StoryListCreateAPIView.as_view(), name="story-list"),
    path("stories/<uuid:story_uuid>/", StoryDetailAPIView.as_view(), name="story-detail"),
    path("stories/<uuid:story_uuid>/viewers/", StoryViewersAPIView.as_view(), name="story-viewers"),
]
