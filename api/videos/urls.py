# app/videos/urls.py
from django.urls import path
from .views import mini_player
from .views_api import api_list, api_upload, api_delete

urlpatterns = [
    path("mini-player/", mini_player, name="mini_player"),

    path("api/videos/list/", api_list, name="api_videos_list"),
    path("api/videos/upload/", api_upload, name="api_videos_upload"),
    path("api/videos/<int:video_id>/delete/", api_delete, name="api_videos_delete"),
]