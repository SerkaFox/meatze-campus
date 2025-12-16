# Archivo: api/views_temp.py

## Tipo de archivo
python

## Funciones
- teacher_temp_create:
    - tipo: function
    - línea: 29
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- teacher_temp_list:
    - tipo: function
    - línea: 99
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- teacher_temp_rotate:
    - tipo: function
    - línea: 131
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- auth_temp_accounts:
    - tipo: function
    - línea: 165
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- auth_temp_verify:
    - tipo: function
    - línea: 189
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- auth_temp_claim:
    - tipo: function
    - línea: 225
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- teacher_alumno_reset_pass:
    - tipo: function
    - línea: 296
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- admin_pending_list:
    - tipo: function
    - línea: 354
    - argumentos: request
    - decoradores: require_admin_token, require_http_methods
- admin_pending_approve_teacher:
    - tipo: function
    - línea: 381
    - argumentos: request, pending_id
    - decoradores: csrf_exempt, require_admin_token, require_http_methods
- admin_pending_mark_student:
    - tipo: function
    - línea: 409
    - argumentos: request, pending_id
    - decoradores: csrf_exempt, require_admin_token, require_http_methods

## Clases
- (ninguna detectada)

## Endpoints detectados (strings)
- (ninguno detectado)
