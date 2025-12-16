# Archivo: api/views.py

## Tipo de archivo
python

## Funciones
- public_cursos_for_temp:
    - tipo: function
    - línea: 40
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- login_password:
    - tipo: function
    - línea: 57
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- require_admin_token:
    - tipo: function
    - línea: 116
    - argumentos: view_func
- _wrapped:
    - tipo: function
    - línea: 118
    - argumentos: request
    - decoradores: wraps
- admin_ping:
    - tipo: function
    - línea: 134
    - argumentos: request
    - decoradores: csrf_exempt, require_admin_token
- admin_cursos_list:
    - tipo: function
    - línea: 141
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- curso_detail:
    - tipo: function
    - línea: 162
    - argumentos: request
    - decoradores: api_view
- _split_last_name:
    - tipo: function
    - línea: 198
    - argumentos: last_name
- admin_teachers_list:
    - tipo: function
    - línea: 210
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- admin_teachers_upsert:
    - tipo: function
    - línea: 252
    - argumentos: request
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_teacher_update:
    - tipo: function
    - línea: 316
    - argumentos: request, user_id
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_teacher_delete:
    - tipo: function
    - línea: 384
    - argumentos: request, user_id
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_cursos_delete:
    - tipo: function
    - línea: 406
    - argumentos: request, curso_id
    - decoradores: csrf_exempt, require_admin_token
- admin_cursos_upsert:
    - tipo: function
    - línea: 425
    - argumentos: request
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_curso_delete:
    - tipo: function
    - línea: 483
    - argumentos: request, curso_id
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_enrolments_list:
    - tipo: function
    - línea: 505
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- admin_cursos_assign:
    - tipo: function
    - línea: 537
    - argumentos: request
    - decoradores: require_admin_token, csrf_exempt, require_http_methods
- admin_fixed_nonlective:
    - tipo: function
    - línea: 597
    - argumentos: request
    - decoradores: csrf_exempt, require_admin_token, require_http_methods
- expand_token_to_dates:
    - tipo: function
    - línea: 637
    - argumentos: y, token
- admin_holidays:
    - tipo: function
    - línea: 728
    - argumentos: request, year
    - decoradores: require_admin_token, require_http_methods
- news_subscribers:
    - tipo: function
    - línea: 786
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- news_wa_inbox:
    - tipo: function
    - línea: 793
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- curso_horario:
    - tipo: function
    - línea: 799
    - argumentos: request, codigo
    - decoradores: csrf_exempt, require_http_methods
- admin_curso_fecha_inicio:
    - tipo: function
    - línea: 903
    - argumentos: request, codigo
    - decoradores: csrf_exempt, require_admin_token, require_http_methods
- curso_horario_save:
    - tipo: function
    - línea: 942
    - argumentos: request, codigo
    - decoradores: api_view, require_admin_token
- admin_auto_schedule:
    - tipo: function
    - línea: 981
    - argumentos: request, codigo
    - decoradores: csrf_exempt, require_http_methods, require_admin_token
- admin_schedule_doc:
    - tipo: function
    - línea: 1053
    - argumentos: request, codigo
    - decoradores: api_view, require_admin_token
- __init__:
    - tipo: function
    - línea: 1071
    - argumentos: self, get_response
- __call__:
    - tipo: function
    - línea: 1074
    - argumentos: self, request
- curso_horario_bulk_delete:
    - tipo: function
    - línea: 1087
    - argumentos: request, codigo
    - decoradores: csrf_exempt, require_http_methods, require_admin_token
- curso_horario_bulk_delete:
    - tipo: function
    - línea: 1121
    - argumentos: request, codigo
    - decoradores: api_view, require_admin_token
- curso_alumnos:
    - tipo: function
    - línea: 1151
    - argumentos: request, codigo
    - decoradores: require_admin_token, require_http_methods
- _inject_headers_footers:
    - tipo: function
    - línea: 1179
    - argumentos: docx_path
- export_docx_graphic:
    - tipo: function
    - línea: 1252
    - argumentos: request
    - decoradores: csrf_exempt, require_http_methods
- request_pin:
    - tipo: function
    - línea: 1330
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes

## Clases
- AdminAuthMiddleware (línea 1070): métodos = __init__, __call__

## Endpoints detectados (strings)
- 
    /meatze/v5/curso?codigo=...
    Один курс по коду.
    
- 
    GET  /meatze/v5/admin/fixed-nonlective?adm=...
         → {"years": {"2025": ["01-13","08-15", ...], ...}}

    POST /meatze/v5/admin/fixed-nonlective?adm=...
         тело: {"years": {"2025": "13/01, 15/01-20/01", "2026": "10/01, 20/06"}}
    
- 
    GET  /meatze/v5/curso/<codigo>/horario?tipo=curso|practica&grupo=...
    POST /meatze/v5/curso/<codigo>/horario?adm=...
         тело: {items:[...], tipo?, grupo?}
    
- 
    GET /meatze/v5/admin/enrolments?codigo=IFCT0209&role=teacher
    Для вкладки "Asignar docentes".
    
- 
    GET /meatze/v5/admin/holidays/<year>?adm=...
    Возвращает кэшированный список праздников ES/ES-PV для фронта.

    Формат ответа:
    {
      "year": 2025,
      "items": [
        {"date": "2025-01-01", "name": "Año Nuevo"},
        ...
      ]
    }
    
- 
    GET /meatze/v5/admin/teachers
    Список преподавателей для панели Docentes.
    Берём всех пользователей с is_staff=True.
    
- 
    GET /meatze/v5/admin/teachers   -> вернуть список (делегируем в admin_teachers_list)
    POST /meatze/v5/admin/teachers  -> создать/обновить преподавателя по email
    
- 
    GET /meatze/v5/curso/<codigo>/alumnos?adm=...

    Возвращает список alumnos, привязанных к курсу через Enrol.
    Пока без заморочек: всех, у кого enrol.codigo = codigo
    (при желании можно отфильтровать role != "teacher").
    
- 
    POST /meatze/v5/admin/curso/<codigo>/auto-schedule?adm=...

    тело: { fecha_inicio: "2025-01-10", grupo: null|"...", hours_per_day?, work_days? }
    → генерирует план через auto_generate_schedule и
      ПОЛНОСТЬЮ перезаписывает расписание курса.
    
- 
    POST /meatze/v5/admin/curso/<codigo>/fecha_inicio?adm=...

    тело: { "fecha": "YYYY-MM-DD" }

    Обновляет поле fecha_inicio у курса с данным código.
    
- 
    POST /meatze/v5/admin/cursos/<id>/delete
    
- 
    POST /meatze/v5/admin/cursos/assign
    тело: {curso_codigo: "...", teachers: ["1","2",...]}
    Обновляет список Enrol с ролью teacher для данного курса.
    
- 
    POST /meatze/v5/admin/cursos/upsert
    тело: {codigo, titulo, modules:[{name, hours}], id?}

    МОДЕЛЬ ИСПОЛЬЗУЕТ JSONField → 
    modules храним как Python list, НЕ как строку!
    
- 
    POST /meatze/v5/admin/teachers/<id>
    Обновление данных преподавателя.
    
- 
    POST /meatze/v5/admin/teachers/<id>/delete
    Убираем статус staff и чистим Enrol с ролью teacher.
    
- 
    POST /meatze/v5/curso/<codigo>/horario/bulk-delete?adm=...
    { fechas: ["2025-01-15", "2025-01-16", ...], tipo?, grupo? }

    Пока игнорируем tipo/grupo и просто удаляем строки Horario по этим датам.
    
- 
    POST /meatze/v5/curso/<codigo>/horario/bulk-delete?adm=...
    {fechas:["2025-01-10", "..."]} → удаляет эти даты у данного курса
    
- /ES
- /horario
- GET /meatze/v5/news/subscribers — заглушка.
- GET /meatze/v5/news/wa-inbox — заглушка.
- https://meatzed.zaindari.eus/meatze/v5/curso/
