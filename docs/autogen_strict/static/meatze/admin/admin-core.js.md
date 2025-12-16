# Archivo: static/meatze/admin/admin-core.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 3
    - argumentos: s, root=...
- $$:
    - tipo: arrow
    - línea: 4
    - argumentos: s, root=...
- tok:
    - tipo: arrow
    - línea: 10
    - argumentos: (sin parámetros)
- setTok:
    - tipo: arrow
    - línea: 11
    - argumentos: t
- qs:
    - tipo: arrow
    - línea: 12
    - argumentos: bust=...
- auth:
    - tipo: arrow
    - línea: 14
    - argumentos: isPost=...
- ping:
    - tipo: function
    - línea: 21
    - argumentos: (sin parámetros)
- tryTokenShared:
    - tipo: function
    - línea: 42
    - argumentos: pwd
- showPanel:
    - tipo: function
    - línea: 104
    - argumentos: mod
- initPanelsOnce:
    - tipo: function
    - línea: 135
    - argumentos: (sin parámetros)

## API bases detectadas
- API_A = API_BASE + '/admin'
- API_BASE = /meatze/v5

## Endpoints detectados (literales)
- (ninguno detectado)

## Endpoints detectados (templates)
- `${API_A}/ping${qs(true)}`

## Endpoints detectados (partes / strings)
- /meatze/v5
- /admin

## Selectores DOM usados
- #adm-pills

## Eventos registrados (addEventListener)
- click @ line 34
- mz:admin-auth @ line 63 (dispatchEvent)
- click @ line 71
- keydown @ line 83
- mz:pane:show @ line 122 (dispatchEvent)
- click @ line 142
- DOMContentLoaded @ line 157

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- fetch @ line 22: arg0={'__template': '`${API_A}/ping${qs(true)}`'}
- addEventListener @ line 34: arg0=click
- dispatchEvent @ line 63: arg0=None
- addEventListener @ line 71: arg0=click
- addEventListener @ line 83: arg0=keydown
- dispatchEvent @ line 122: arg0=None
- addEventListener @ line 142: arg0=click
- addEventListener @ line 157: arg0=DOMContentLoaded

## Variables globales declaradas
- $
- $$
- API_BASE
- API_A
- tok
- setTok
- qs
- auth
- ping
- gate
- pills
- pillBtns
- tryTokenShared
- map
- showPanel
- initPanelsOnce
