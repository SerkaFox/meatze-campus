# Archivo: api/admin_views.py

## Tipo de archivo
python

## Funciones
- _check_admin:
    - tipo: function
    - línea: 12
    - argumentos: request
- admin_teachers:
    - tipo: function
    - línea: 27
    - argumentos: request
    - decoradores: api_view
- admin_teacher_update:
    - tipo: function
    - línea: 89
    - argumentos: request, pk
    - decoradores: api_view
- admin_teacher_delete:
    - tipo: function
    - línea: 127
    - argumentos: request, pk
    - decoradores: api_view
- _curso_to_item:
    - tipo: function
    - línea: 146
    - argumentos: c
- admin_cursos_list:
    - tipo: function
    - línea: 157
    - argumentos: request
    - decoradores: api_view
- admin_cursos_upsert:
    - tipo: function
    - línea: 171
    - argumentos: request
    - decoradores: api_view
- admin_curso_delete:
    - tipo: function
    - línea: 223
    - argumentos: request, pk
    - decoradores: api_view
- admin_enrolments:
    - tipo: function
    - línea: 240
    - argumentos: request
    - decoradores: api_view
- admin_cursos_assign:
    - tipo: function
    - línea: 274
    - argumentos: request
    - decoradores: api_view

## Clases
- (ninguna detectada)

## Endpoints detectados (strings)
- 
    GET  /meatze/v5/admin/teachers
    POST /meatze/v5/admin/teachers   (upsert по email)
    
- 
    GET /meatze/v5/admin/cursos
    
- 
    GET /meatze/v5/admin/enrolments?codigo=IFCT0209&role=teacher
    
- 
    POST /meatze/v5/admin/cursos/<id>/delete
    
- 
    POST /meatze/v5/admin/cursos/assign
    Body: { curso_codigo: "IFCT0209", teachers: ["12","34",...] }
    
- 
    POST /meatze/v5/admin/cursos/upsert

    Body: { codigo, titulo, modules: [ {name, hours}, ... ], id? }
    
- 
    POST /meatze/v5/admin/teachers/<id>
    
- 
    POST /meatze/v5/admin/teachers/<id>/delete
    Важно: лучше НЕ удалять юзера, а просто снять флаг is_teacher.
    
