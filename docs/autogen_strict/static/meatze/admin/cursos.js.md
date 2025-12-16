# Archivo: static/meatze/admin/cursos.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 3
    - argumentos: s
- tok:
    - tipo: arrow
    - línea: 6
    - argumentos: (sin parámetros)
- qs:
    - tipo: arrow
    - línea: 7
    - argumentos: bust=...
- auth:
    - tipo: arrow
    - línea: 8
    - argumentos: isPost=...
- apiJSON:
    - tipo: function
    - línea: 9
    - argumentos: url, opt=...
- toModulesArray:
    - tipo: function
    - línea: 22
    - argumentos: modsRaw
- esc:
    - tipo: arrow
    - línea: 50
    - argumentos: s
- normId:
    - tipo: arrow
    - línea: 51
    - argumentos: v
- parseModulesBasic:
    - tipo: function
    - línea: 74
    - argumentos: text
- updateCounters:
    - tipo: function
    - línea: 160
    - argumentos: (sin parámetros)
- setTab:
    - tipo: function
    - línea: 169
    - argumentos: which
- loadList:
    - tipo: function
    - línea: 224
    - argumentos: (sin parámetros)
- buildTeacherChips:
    - tipo: function
    - línea: 347
    - argumentos: teachers, assignedSet
- getSelectedTeacherIdsFromChips:
    - tipo: function
    - línea: 364
    - argumentos: (sin parámetros)
- renderAssignedBadges:
    - tipo: function
    - línea: 367
    - argumentos: enrolItems
- loadAssignForm:
    - tipo: function
    - línea: 377
    - argumentos: force=...
- updateAssignedTeachers:
    - tipo: function
    - línea: 402
    - argumentos: (sin parámetros)
- initCursosOnce:
    - tipo: function
    - línea: 20
    - argumentos: (sin parámetros)

## API bases detectadas
- API_A = API_BASE + '/admin'
- API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5'

## Endpoints detectados (literales)
- (ninguno detectado)

## Endpoints detectados (templates)
- `${API_A}/cursos/upsert${qs()}`
- `${API_A}/cursos${qs(true)}`
- `${API_A}/cursos/${it.id}/delete${qs()}`
- `${API_A}/teachers${qs(true)}`
- `${API_A}/cursos/assign${qs()}`

## Endpoints detectados (partes / strings)
- /
- /meatze/v5
- /admin

## Selectores DOM usados
- #ui-cursos
- #mzc-tab-form
- #mzc-tab-assign
- #mzc-pane-form
- #mzc-pane-assign
- #mzc-cf-titulo
- #mzc-cf-codigo
- #mzc-cf-modulos
- #mzc-cf-total-horas
- #mzc-cf-total-modulos
- #mzc-cf-msg
- #mzc-cf-list
- #mzc-ca-curso
- #mzc-ca-codigo
- #mzc-ca-msg
- #mzc-ca-teachers-chips
- #mzc-cf-save
- #mzc-cf-clear
- #mzc-ca-assigned
- #mzc-ca-reload
- #mzc-ca-assign

## Eventos registrados (addEventListener)
- input @ line 165
- paste @ line 166
- mz:cursos-updated @ line 213 (dispatchEvent)
- mz:cursos-updated @ line 331 (dispatchEvent)
- click @ line 357
- change @ line 414
- click @ line 415
- click @ line 421
- mz:admin-auth @ line 443
- mz:pane:show @ line 446

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- fetch @ line 10: arg0=None
- addEventListener @ line 165: arg0=input
- addEventListener @ line 166: arg0=paste
- apiJSON @ line 203: arg0={'__template': '`${API_A}/cursos/upsert${qs()}`'}
- dispatchEvent @ line 213: arg0=None
- apiJSON @ line 226: arg0={'__template': '`${API_A}/cursos${qs(true)}`'}
- apiJSON @ line 324: arg0={'__template': '`${API_A}/cursos/${it.id}/delete${qs()}`'}
- dispatchEvent @ line 331: arg0=None
- addEventListener @ line 357: arg0=click
- apiJSON @ line 381: arg0={'__template': '`${API_A}/cursos${qs(true)}`'}
- apiJSON @ line 394: arg0={'__template': '`${API_A}/teachers${qs(true)}`'}
- apiJSON @ line 408: arg0=None
- addEventListener @ line 414: arg0=change
- addEventListener @ line 415: arg0=click
- apiJSON @ line 425: arg0={'__template': '`${API_A}/cursos/assign${qs()}`'}
- addEventListener @ line 421: arg0=click
- addEventListener @ line 443: arg0=mz:admin-auth
- addEventListener @ line 446: arg0=mz:pane:show

## Variables globales declaradas
- $
- API_BASE
- API_A
- tok
- qs
- auth
- apiJSON
- cursosReady
- editingId
- initCursosOnce
