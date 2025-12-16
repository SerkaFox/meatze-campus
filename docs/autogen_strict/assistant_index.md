# Assistant Index (strict)

Este archivo es un índice consolidado para el asistente. No contiene inferencias: sólo hechos extraídos.

## Routes

- `me` → `api.auth_views.me_view`
- `(non-literal)` → `core.views.home` (name=`home`)
  - templates: `home.html`
  - page_keys: `tpl:home`
- `alumno/` → `(unresolved)`
- `admin-panel/` → `core.views.admin_panel` (name=`admin_panel`)
  - templates: `meatze_admin/base_admin.html`
  - page_keys: `admin:base_admin`
- `meatze/v5/me` → `api.auth_views.me_view` (name=`meatze-me`)
- `meatze/v5/me/profile` → `api.profile_views.me_profile`
- `meatze/v5/me/password` → `api.profile_views.me_change_password`
- `meatze/v5/admin/ping` → `api.views.admin_ping`
- `meatze/v5/notify/subscribers` → `api.notify_views.subscribers`
- `meatze/v5/notify/wa-upsert` → `api.notify_views.wa_upsert`
- `meatze/v5/notify/wa-toggle` → `api.notify_views.wa_toggle`
- `meatze/v5/notify/wa-delete` → `api.notify_views.wa_delete`
- `meatze/v5/notify/wa-import` → `api.notify_views.wa_import`
- `meatze/v5/notify/upload-wa` → `api.notify_views.upload_wa`
- `meatze/v5/notify/broadcast` → `api.notify_views.broadcast`
- `meatze/v5/notify/wa-clear` → `api.notify_views.wa_clear`
- `meatze/v6/ws-webhook` → `api.notify_views.ws_webhook`
- `meatze/v5/auth/login_password` → `api.auth_views.login_password` (name=`meatze-login-password`)
- `meatze/v5/auth/set_password` → `api.auth_views.set_password` (name=`meatze-set-password`)
- `meatze/v5/auth/logout` → `api.auth_views.logout_view` (name=`meatze-logout`)
- `meatze/v5/auth/request_pin` → `api.auth_views.request_pin`
- `meatze/v5/auth/verify_pin` → `api.auth_views.verify_pin`
- `meatze/v5/teacher/temp/create` → `api.views_temp.teacher_temp_create`
- `meatze/v5/teacher/temp/list` → `api.views_temp.teacher_temp_list`
- `meatze/v5/teacher/temp/rotate` → `api.views_temp.teacher_temp_rotate`
- `meatze/v5/auth/temp_cursos` → `api.views.public_cursos_for_temp`
- `meatze/v5/auth/temp_accounts` → `api.views_temp.auth_temp_accounts`
- `meatze/v5/auth/temp_verify` → `api.views_temp.auth_temp_verify`
- `meatze/v5/auth/temp_claim` → `api.views_temp.auth_temp_claim`
- `meatze/v5/teacher/alumno/reset_pass` → `api.views_temp.teacher_alumno_reset_pass`
- `meatze/v5/ai/warmup` → `api.views_ai.ai_warmup`
- `meatze/v5/ai/ask` → `api.views_ai.ai_ask`
- `meatze/v5/ai/help` → `api.views_ai.ai_help`
- `meatze/v5/admin/teachers` → `api.views.admin_teachers_upsert`
- `meatze/v5/admin/teachers/<int:user_id>` → `api.views.admin_teacher_update`
- `meatze/v5/admin/teachers/<int:user_id>/delete` → `api.views.admin_teacher_delete`
- `meatze/v5/admin/cursos` → `api.views.admin_cursos_list`
- `meatze/v5/admin/cursos/upsert` → `api.views.admin_cursos_upsert`
- `meatze/v5/curso/<str:codigo>/alumnos` → `api.views.curso_alumnos`
- `meatze/v5/admin/cursos/<int:curso_id>/delete` → `api.views.admin_curso_delete`
- `meatze/v5/curso/<str:codigo>/horario` → `api.views.curso_horario`
- `meatze/v5/curso/<str:codigo>/horario/save` → `api.views.curso_horario`
- `meatze/v5/curso/<str:codigo>/horario/bulk-delete` → `api.views.curso_horario_bulk_delete`
- `meatze/v5/admin/curso/<str:codigo>/auto-schedule` → `api.views.admin_auto_schedule`
- `meatze/v5/admin/curso/<str:codigo>/fecha_inicio` → `api.views.admin_curso_fecha_inicio`
- `meatze/v5/export-docx-graphic` → `api.views.export_docx_graphic`
- `meatze/v5/admin/enrolments` → `api.views.admin_enrolments_list`
- `meatze/v5/admin/cursos/assign` → `api.views.admin_cursos_assign`
- `meatze/v5/admin/fixed-nonlective` → `api.views.admin_fixed_nonlective`
- `meatze/v5/admin/holidays/<int:year>` → `api.views.admin_holidays`
- `meatze/v5/news/subscribers` → `api.views.news_subscribers`
- `meatze/v5/notify/wa-inbox` → `api.notify_views.wa_inbox`
- `panel/` → `(unresolved)`

## Pages

### admin:base_admin
- templates: 1
- scripts: 0
- ui.ids: 6
- ui.classes: 9
- actions: 0

### admin:cursos
- templates: 1
- scripts: 1
- ui.ids: 21
- ui.classes: 12
- actions: 8
  - input on `(unknown selector)`
  - paste on `(unknown selector)`
  - click on `(unknown selector)`
  - change on `(unknown selector)`
  - click on `#mzc-ca-reload`
  - click on `#mzc-ca-assign`
  - ... (+2)

### admin:horarios
- templates: 1
- scripts: 0
- ui.ids: 51
- ui.classes: 33
- actions: 0

### admin:subs
- templates: 1
- scripts: 0
- ui.ids: 36
- ui.classes: 12
- actions: 0

### admin:teachers
- templates: 1
- scripts: 1
- ui.ids: 15
- ui.classes: 9
- actions: 8
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - input on `(unknown selector)`
  - input on `(unknown selector)`
  - click on `(unknown selector)`
  - click on `#mzt-save`
  - ... (+2)

### admin:wa
- templates: 1
- scripts: 1
- ui.ids: 12
- ui.classes: 8
- actions: 8
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - change on `(unknown selector)`
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - ... (+2)

### js:chat-widget
- templates: 0
- scripts: 1
- ui.ids: 0
- ui.classes: 0
- actions: 6
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - click on `(unknown selector)`
  - keydown on `(unknown selector)`
  - click on `(unknown selector)`
  - keydown on `(unknown selector)`

### panel:alumno_home
- templates: 1
- scripts: 0
- ui.ids: 0
- ui.classes: 8
- actions: 0

### panel:alumnos
- templates: 1
- scripts: 0
- ui.ids: 13
- ui.classes: 22
- actions: 0

### panel:calendario
- templates: 1
- scripts: 0
- ui.ids: 9
- ui.classes: 14
- actions: 0

### panel:chat
- templates: 1
- scripts: 0
- ui.ids: 13
- ui.classes: 40
- actions: 0

### panel:course_panel
- templates: 1
- scripts: 0
- ui.ids: 4
- ui.classes: 17
- actions: 0

### panel:ia
- templates: 1
- scripts: 0
- ui.ids: 19
- ui.classes: 38
- actions: 0

### panel:info
- templates: 1
- scripts: 0
- ui.ids: 0
- ui.classes: 15
- actions: 0

### panel:materiales
- templates: 1
- scripts: 0
- ui.ids: 4
- ui.classes: 43
- actions: 0

### tpl:base
- templates: 1
- scripts: 0
- ui.ids: 59
- ui.classes: 34
- actions: 0

### tpl:chat_widget
- templates: 1
- scripts: 0
- ui.ids: 7
- ui.classes: 15
- actions: 0

### tpl:home
- templates: 1
- scripts: 0
- ui.ids: 4
- ui.classes: 25
- actions: 0
