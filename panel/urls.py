# panel/urls.py
from django.urls import path
from . import views
from panel.views_events import log_learning_event_panel
from .views_attendance import (
    attendance_request,
    attendance_heartbeat,
    teacher_attendance_pending,
    teacher_attendance_decide,
)
app_name = "panel"

urlpatterns = [
    path("", views.alumno_home, name="alumno_home"),
    path("curso/<str:codigo>/", views.course_panel, name="course"),
    path("materiales/download/<int:file_id>/", views.material_download, name="material_download"),
    path("curso/<str:codigo>/alumnos/status", views.alumnos_status, name="alumnos_status"),
    path("v5/event", log_learning_event_panel, name="event"),
    path("curso/<str:codigo>/tareas/<int:task_id>/download/", views.task_download, name="task_download"),
    path("curso/<str:codigo>/tareas/<int:task_id>/submission/<int:sub_id>/download/", views.submission_download, name="submission_download"),
    path("alumno/materiales/share-link/<int:file_id>/", views.material_share_link_create, name="material_share_link_create"),
    path("s/<str:token>/", views.public_share_download, name="public_share_download"),

    path("meatze/v5/attendance/request", attendance_request),
    path("meatze/v5/attendance/heartbeat", attendance_heartbeat),
    path("curso/<str:codigo>/physical_report_doc/", views.teacher_physical_report_doc, name="physical_report_doc"),


    path("meatze/v5/teacher/attendance/pending", teacher_attendance_pending),
    path("meatze/v5/teacher/attendance/decide", teacher_attendance_decide),

]