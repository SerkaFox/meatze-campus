# shortshare/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="short_index"),
    path("<str:code>/", views.room_view, name="short_room"),
    path("<str:code>/upload/", views.upload, name="short_upload"),
    path("<str:code>/f/<int:file_id>/", views.download, name="short_download"),
    path("<str:code>/del/<int:file_id>/", views.delete_file, name="short_delete"),
    path("<str:code>/link/add/", views.add_link, name="short_add_link"),
    path("<str:code>/link/del/<int:link_id>/", views.delete_link, name="short_delete_link"),
    path("<str:code>/v/<int:file_id>/", views.view_file, name="short_view"),
    path("<str:code>/i/<int:file_id>/", views.inline_file, name="short_inline"),
    path("<str:code>/link/ext/<int:link_id>/", views.extend_link, name="short_extend_link"),
]