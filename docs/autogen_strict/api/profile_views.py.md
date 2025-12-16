# Archivo: api/profile_views.py

## Tipo de archivo
python

## Funciones
- _get_or_create_profile:
    - tipo: function
    - línea: 14
    - argumentos: user
- me_change_password:
    - tipo: function
    - línea: 20
    - argumentos: request
    - decoradores: csrf_exempt, login_required
- _build_profile_dict:
    - tipo: function
    - línea: 53
    - argumentos: user, profile
- me_profile:
    - tipo: function
    - línea: 87
    - argumentos: request
    - decoradores: csrf_exempt, login_required
- user_display:
    - tipo: function
    - línea: 134
    - argumentos: request
    - decoradores: api_view, permission_classes

## Clases
- (ninguna detectada)

## Endpoints detectados (strings)
- 
    GET  /meatze/v5/me/profile  -> вернуть профиль
    POST /meatze/v5/me/profile  -> сохранить профиль
    
- 
    GET /meatze/v5/user_display?email=...
    Возвращает красивое имя для e-mail.
    
- 
    POST /meatze/v5/me/password
    { "password": "...." }

    Меняет пароль текущему залогиненному пользователю.
    
