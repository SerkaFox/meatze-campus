# Archivo: api/auth_views.py

## Tipo de archivo
python

## Funciones
- get_django_request:
    - tipo: function
    - línea: 26
    - argumentos: req
- build_me:
    - tipo: function
    - línea: 33
    - argumentos: user
- request_pin:
    - tipo: function
    - línea: 51
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- verify_pin:
    - tipo: function
    - línea: 99
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- set_password:
    - tipo: function
    - línea: 165
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- logout_view:
    - tipo: function
    - línea: 264
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes
- login_password:
    - tipo: function
    - línea: 281
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- me_view:
    - tipo: function
    - línea: 319
    - argumentos: request
    - decoradores: csrf_exempt, api_view, permission_classes, authentication_classes

## Clases
- (ninguna detectada)

## Endpoints detectados (strings)
- 
    GET /meatze/v5/me

    Возвращает текущего юзера по сессии:
    { "me": { ... } } или { "me": null }, если не залогинен.
    
- 
    POST /meatze/v5/auth/logout
    
- 
    POST /meatze/v5/auth/request_pin
    { "email": "..." }

    Создаёт 6-значный PIN и отправляет на почту.
    PIN действует 10 минут.
    
- 
    POST /meatze/v5/auth/verify_pin
    { "email": "...", "pin": "123456" }

    Проверяет PIN, создаёт/находит пользователя, логинит через сессию,
    возвращает {me:{...}}.
    
