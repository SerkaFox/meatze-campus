from django.urls import path
from . import views, views_temp

urlpatterns = [
    path("cursos", views.cursos_list),
    path("curso/<str:codigo>", views.curso_detail),
    path("me", views.me),
    path("me/profile", views.me_profile),
    path("auth/login_password", views.login_password),
    path("auth/request_pin", views.request_pin),
    path("auth/verify_pin", views.verify_pin),
    path("auth/set_password", views.set_password),
    path("auth/logout", views.logout),
    path("admin/ping", views.admin_ping, name="admin_ping"),
]
