# panel/urls.py
from django.urls import path
from . import views

app_name = "panel"

urlpatterns = [
    path("", views.alumno_home, name="alumno_home"),        # /alumno/
    path("curso/<slug:codigo>/", views.course_panel, name="course"),
]
