from django.urls import path
from . import views

urlpatterns = [
    # твоя личная (управление/загрузка/создание плейлистов)
    path("mini-player/", views.mini_player, name="mini_player"),
    path("mini-player/upload/", views.video_upload, name="mini_player_upload"),
    path("mini-player/delete/<int:video_id>/", views.video_delete, name="mini_player_delete"),

    path("playlists/create/", views.playlist_create, name="playlist_create"),
    path("playlists/<int:playlist_id>/add/<int:video_id>/", views.playlist_add, name="playlist_add"),
    path("playlists/<int:playlist_id>/remove/<int:video_id>/", views.playlist_remove, name="playlist_remove"),
    path("playlists/<int:playlist_id>/toggle-public/", views.playlist_toggle_public, name="playlist_toggle_public"),

    # гостевая по ссылке: только выбранные видео
    path("p/<str:token>/", views.playlist_public, name="playlist_public"),
]
urlpatterns += [
    path("embed/<str:token>/", views.playlist_embed, name="playlist_embed"),
    # ✅ help bindings admin
    path("help/create/", views.helpbinding_create, name="helpbinding_create"),
    path("help/<int:binding_id>/update/", views.helpbinding_update, name="helpbinding_update"),
    path("help/<int:binding_id>/toggle/", views.helpbinding_toggle, name="helpbinding_toggle"),
    path("help/<int:binding_id>/delete/", views.helpbinding_delete, name="helpbinding_delete"),
]