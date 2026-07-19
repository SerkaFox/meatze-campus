from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static
from core.views import home 
from api import views as api_views
from api import auth_views as api_auth
from api import profile_views as api_profile
from api import views_temp
from api import views_ai
from api import notify_views
from api.views_ai import ai_ask, ai_warmup, ai_help
from api.views_events import log_learning_event, admin_lanbide_activity, admin_lanbide_daily
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from api.views_horario_day import horario_day, horario_slot_delete, horario_day_delete
class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "home",
            "privacy_policy",
            "terms_of_service",
        ]

    def location(self, item):
        return reverse(item)

sitemaps = {
    "static": StaticViewSitemap(),
}

from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        "api": "MEATZE API",
        "version": "v5"
    })
    
    

urlpatterns = [
    path("me", api_auth.me_view),
    path("v5", api_root),
    path("", home, name="home"),
    path("videos/", include("api.videos.urls")),
    path("alumno/", include("panel.urls", namespace="panel")),
    path("acceder/", api_views.acceder, name="acceder"),

    path("admin-panel/", core_views.admin_panel, name="admin_panel"),
    path("v5/me", api_auth.me_view, name="meatze-me"),
    path("v5/me/profile", api_profile.me_profile),
    path("v5/me/password", api_profile.me_change_password),

    # admin utils
    path("v5/admin/ping", api_views.admin_ping),
    
    path("v5/notify/subscribers", notify_views.subscribers),
    path("v5/notify/wa-upsert", notify_views.wa_upsert),
    path("v5/notify/wa-toggle", notify_views.wa_toggle),
    path("v5/notify/wa-inbox-delete", notify_views.wa_inbox_delete),
    path("v5/notify/wa-import", notify_views.wa_import),
    path("v5/notify/upload-wa", notify_views.upload_wa),
    path("v5/notify/broadcast", notify_views.broadcast),
    path("v5/notify/wa-clear", notify_views.wa_clear),
    path("v5/notify/wa-reply", notify_views.wa_reply),
    



    # webhook от Meta
    path("meatze/v6/ws-webhook", notify_views.ws_webhook),
    # AUTH
    path("v5/auth/login_password", api_auth.login_password, name="meatze-login-password"),
    path("v5/auth/set_password", api_auth.set_password, name="meatze-set-password"),
    path("v5/auth/logout", api_auth.logout_view, name="meatze-logout"),
    path("v5/auth/request_pin", api_auth.request_pin),
    path("v5/auth/verify_pin", api_auth.verify_pin),


    path("v5/teacher/temp/create", views_temp.teacher_temp_create),
    path("v5/teacher/temp/list", views_temp.teacher_temp_list),
    path("v5/teacher/temp/rotate", views_temp.teacher_temp_rotate),

    path("v5/auth/temp_cursos", api_views.public_cursos_for_temp),
    path("v5/auth/temp_accounts", views_temp.auth_temp_accounts),
    path("v5/auth/temp_verify", views_temp.auth_temp_verify),
    path("v5/auth/temp_claim", views_temp.auth_temp_claim),

    path("v5/teacher/alumno/reset_pass", views_temp.teacher_alumno_reset_pass),
    path("v5/ai/warmup", views_ai.ai_warmup),
    path("v5/ai/ask", views_ai.ai_ask),
    path("v5/ai/help", ai_help),
    
    # docentes
    
    path("v5/admin/teachers", api_views.admin_teachers_upsert),
    path("v5/admin/teachers/<int:user_id>", api_views.admin_teacher_update),
    path("v5/admin/teachers/<int:user_id>/delete", api_views.admin_teacher_delete),

    # cursos
    path("v5/admin/cursos", api_views.admin_cursos_list),
    path("v5/admin/cursos/upsert", api_views.admin_cursos_upsert),
    path("v5/curso/<str:codigo>/alumnos", api_views.curso_alumnos),
    path("v5/admin/cursos/<int:curso_id>/delete", api_views.admin_curso_delete),
    
    path("v5/curso/<str:codigo>/horario", api_views.curso_horario),
    path("v5/curso/<str:codigo>/horario/save", api_views.curso_horario),
    path("v5/curso/<str:codigo>/horario/bulk-delete", api_views.curso_horario_bulk_delete),
    path("v5/admin/curso/<str:codigo>/auto-schedule", api_views.admin_auto_schedule),
    path("v5/admin/curso/<str:codigo>/fecha_inicio", api_views.admin_curso_fecha_inicio),
    path("v5/export-docx-graphic", api_views.export_docx_graphic),


    # asignación docentes
    path("v5/admin/enrolments", api_views.admin_enrolments_list),
    path("v5/admin/cursos/assign", api_views.admin_cursos_assign),


    # заглушки
    path("v5/admin/fixed-nonlective", api_views.admin_fixed_nonlective),
    path("v5/admin/holidays/<int:year>", api_views.admin_holidays),
    path("v5/news/subscribers", api_views.news_subscribers),
    path("v5/notify/wa-inbox", notify_views.wa_inbox),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
from api import views_chat

urlpatterns += [
    path("v5/chat/<str:codigo>/messages", views_chat.chat_messages),
    path("v5/chat/<str:codigo>/messages/<int:msg_id>", views_chat.chat_delete_message),
    path("v5/chat/<str:codigo>/deleted", views_chat.chat_deleted_since),
    path("v5/chat/<str:codigo>/react", views_chat.chat_react),
    path("v5/chat/<str:codigo>/react_summary", views_chat.chat_react_summary),
    path("v5/chat/<str:codigo>/read", views_chat.chat_read),
    path("v5/chat/<str:codigo>/unread", views_chat.chat_unread),
    path("v5/chat/<str:codigo>/teachers", views_chat.chat_teachers),
    path("v5/chat/<str:codigo>/dm_peers", views_chat.chat_dm_peers),
    path("chat/<str:codigo>/dm_unread_map", views_chat.chat_dm_unread_map),
    path("v5/chat/<str:codigo>/dm_unread_map", views_chat.chat_dm_unread_map),

    path("v5/user_display", api_profile.user_display),
    path("v5/admin/pending", views_temp.admin_pending_list),
    
    path("privacy/", api_views.privacy_policy, name="privacy_policy"),
    path("terms/", api_views.terms_of_service, name="terms_of_service"),

    path("v5/admin/pending/<int:pending_id>/approve-teacher", views_temp.admin_pending_approve_teacher),
    path("v5/admin/pending/<int:pending_id>/mark-student", views_temp.admin_pending_mark_student),
]

urlpatterns += [
    path("v5/event", log_learning_event),
    path("v5/admin/lanbide/activity", admin_lanbide_activity),
    path("v5/admin/lanbide/daily", admin_lanbide_daily),
    path("v5/admin/lanbide/material_status", api_views.admin_material_status, name="admin_material_status"),
]
from panel.views_attendance import attendance_request, attendance_heartbeat, teacher_attendance_pending, teacher_attendance_decide

urlpatterns += [
    path("v5/attendance/request", attendance_request),
    path("v5/attendance/heartbeat", attendance_heartbeat),
    path("v5/teacher/attendance/pending", teacher_attendance_pending),
    path("v5/teacher/attendance/decide", teacher_attendance_decide),
]

urlpatterns += [
    path("v5/admin/curso/<str:codigo>/nonlective", api_views.admin_curso_nonlective),
    path("v5/admin/curso/<str:codigo>/nonlective/effective", api_views.admin_curso_nonlective_effective),
    path("v5/admin/curso/<str:codigo>/horario/day", horario_day, name="mz_horario_day"),
    path("v5/admin/curso/<str:codigo>/horario/day/delete", horario_day_delete, name="mz_horario_day_delete"),
    path("v5/admin/curso/<str:codigo>/horario/slot/<int:slot_id>/delete", horario_slot_delete, name="mz_horario_slot_delete"),
    path("room/", include("panel.shortshare.urls"), name="room"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap",),
]
from api import help_views

urlpatterns += [
    path("help/context", help_views.help_context, name="help_context_legacy"),
    path("v5/help/context", help_views.help_context, name="help_context"),
]

