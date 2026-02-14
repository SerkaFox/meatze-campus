# panel/urls.py
from django.urls import path
from . import views
from . import reports
from panel.views_events import log_learning_event_panel
from .views_attendance import (
    attendance_request,
    attendance_heartbeat,
    teacher_attendance_pending,
    teacher_attendance_decide,
)
from .AnexoVI import anexo_vi_doc

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
    path("curso/<str:codigo>/tareas/anexo-vi.docx", reports.teacher_anexo_vi_report_doc, name="anexo_vi_docx"),
    path("meatze/v5/teacher/attendance/pending", teacher_attendance_pending),
    path("meatze/v5/teacher/attendance/decide", teacher_attendance_decide),
    path("anexo_vi/<str:codigo>/<int:alumno_id>/", anexo_vi_doc, name="anexo_vi"),
]

# panel/urls.py
from django.urls import path
from .views_materiales_api import materiales_upload_files_ajax, materiales_upload_folder_bundle

urlpatterns += [
    path("meatze/v5/materiales/upload_files_ajax/", materiales_upload_files_ajax, name="mz_upload_files_ajax"),
    path("meatze/v5/materiales/upload_folder_bundle/", materiales_upload_folder_bundle, name="mz_upload_folder_bundle"),
]

# panel/urls.py
from django.urls import path
from . import views_live
from . import views_materiales_api as mza

urlpatterns += [
    path("curso/<int:curso_id>/live/", views_live.curso_live, name="curso_live"),
    path("materiales/zip/", mza.materiales_download_zip, name="materiales_download_zip"),
    
]
from panel.views_modules_access import teacher_student_modules_get, teacher_student_modules_set
urlpatterns += [
    path("meatze/v5/teacher/student-modules/get", teacher_student_modules_get, name="teacher_student_modules_get"),
    path("meatze/v5/teacher/student-modules/set", teacher_student_modules_set, name="teacher_student_modules_set"),
]