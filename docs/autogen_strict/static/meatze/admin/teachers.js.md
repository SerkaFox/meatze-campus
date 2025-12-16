# Archivo: static/meatze/admin/teachers.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 2
    - argumentos: s
- tok:
    - tipo: arrow
    - línea: 7
    - argumentos: (sin parámetros)
- qs:
    - tipo: arrow
    - línea: 8
    - argumentos: bust=...
- auth:
    - tipo: arrow
    - línea: 9
    - argumentos: isPost=...
- apiJSON:
    - tipo: function
    - línea: 10
    - argumentos: url, opt=...
- esc:
    - tipo: arrow
    - línea: 23
    - argumentos: s
- escAttr:
    - tipo: arrow
    - línea: 24
    - argumentos: s
- nrm:
    - tipo: arrow
    - línea: 25
    - argumentos: s
- debounce:
    - tipo: arrow
    - línea: 26
    - argumentos: fn, ms=...
- refreshPending:
    - tipo: function
    - línea: 45
    - argumentos: (sin parámetros)
- pendingRow:
    - tipo: function
    - línea: 57
    - argumentos: it
- drawPending:
    - tipo: function
    - línea: 95
    - argumentos: items
- applyPendingFilter:
    - tipo: function
    - línea: 105
    - argumentos: (sin parámetros)
- refreshList:
    - tipo: function
    - línea: 123
    - argumentos: (sin parámetros)
- rowView:
    - tipo: function
    - línea: 134
    - argumentos: it
- rowEdit:
    - tipo: function
    - línea: 151
    - argumentos: it
- doDelete:
    - tipo: function
    - línea: 186
    - argumentos: id
- drawRows:
    - tipo: function
    - línea: 194
    - argumentos: items
- applyFilter:
    - tipo: function
    - línea: 200
    - argumentos: (sin parámetros)
- initTeachersOnce:
    - tipo: function
    - línea: 20
    - argumentos: (sin parámetros)

## API bases detectadas
- API_A = API_BASE + '/admin'
- API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5'

## Endpoints detectados (literales)
- (ninguno detectado)

## Endpoints detectados (templates)
- `${API_A}/teachers${qs(true)}`
- `${API_A}/teachers/${it.id}${qs()}`
- `${API_A}/teachers/${id}/delete${qs()}`
- `${API_A}/teachers${qs()}`

## Endpoints detectados (partes / strings)
- /
- /meatze/v5
- /admin
- /admin/pending

## Selectores DOM usados
- #mzt-body
- #mzt-search
- #mzt-clear
- #mzt-msg
- #mzp-body
- #mzp-search
- #mzp-refresh
- #mzp-clear
- #mzt-save
- #mzt-email
- #mzt-first
- #mzt-last1
- #mzt-last2
- #mzt-bio
- #ui-teachers

## Eventos registrados (addEventListener)
- click @ line 115
- click @ line 116
- input @ line 117
- input @ line 210
- click @ line 211
- click @ line 214
- mz:admin-auth @ line 245
- mz:pane:show @ line 248

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- fetch @ line 11: arg0=None
- apiJSON @ line 49: arg0={'__template': '`${PEND_BASE}${qs(true)}`'}
- apiJSON @ line 77: arg0={'__template': '`${PEND_BASE}/${it.id}/approve-teacher${qs()}`'}
- apiJSON @ line 87: arg0={'__template': '`${PEND_BASE}/${it.id}/mark-student${qs()}`'}
- addEventListener @ line 115: arg0=click
- addEventListener @ line 116: arg0=click
- addEventListener @ line 117: arg0=input
- apiJSON @ line 126: arg0={'__template': '`${API_A}/teachers${qs(true)}`'}
- apiJSON @ line 179: arg0={'__template': '`${API_A}/teachers/${it.id}${qs()}`'}
- apiJSON @ line 189: arg0={'__template': '`${API_A}/teachers/${id}/delete${qs()}`'}
- addEventListener @ line 210: arg0=input
- addEventListener @ line 211: arg0=click
- apiJSON @ line 227: arg0={'__template': '`${API_A}/teachers${qs()}`'}
- addEventListener @ line 214: arg0=click
- addEventListener @ line 245: arg0=mz:admin-auth
- addEventListener @ line 248: arg0=mz:pane:show

## Variables globales declaradas
- $
- API_BASE
- API_A
- tok
- qs
- auth
- apiJSON
- teachersReady
- initTeachersOnce
