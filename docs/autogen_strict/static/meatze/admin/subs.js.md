# Archivo: static/meatze/admin/subs.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 4
    - argumentos: s, root=...
- tok:
    - tipo: arrow
    - línea: 18
    - argumentos: (sin parámetros)
- qs:
    - tipo: arrow
    - línea: 19
    - argumentos: bust=...
- auth:
    - tipo: arrow
    - línea: 20
    - argumentos: isPost=...
- apiJSON:
    - tipo: function
    - línea: 26
    - argumentos: url, opt=...
- sleep:
    - tipo: function
    - línea: 34
    - argumentos: ms
- renderSelectedRecipients:
    - tipo: function
    - línea: 37
    - argumentos: (sin parámetros)
- addWaSelected:
    - tipo: function
    - línea: 102
    - argumentos: num
- syncPicked:
    - tipo: function
    - línea: 109
    - argumentos: (sin parámetros)
- showProgress:
    - tipo: function
    - línea: 116
    - argumentos: main, sub=...
- updateProgress:
    - tipo: function
    - línea: 124
    - argumentos: main, sub
- hideProgress:
    - tipo: function
    - línea: 132
    - argumentos: (sin parámetros)
- getPreviewName:
    - tipo: function
    - línea: 138
    - argumentos: (sin parámetros)
- getCurrentFile:
    - tipo: function
    - línea: 169
    - argumentos: (sin parámetros)
- applyWaSearchFilter:
    - tipo: function
    - línea: 174
    - argumentos: (sin parámetros)
- updatePreview:
    - tipo: function
    - línea: 189
    - argumentos: (sin parámetros)
- handleWaImport:
    - tipo: function
    - línea: 252
    - argumentos: (sin parámetros)
- loadSubs:
    - tipo: function
    - línea: 300
    - argumentos: (sin parámetros)
- drawSubs:
    - tipo: function
    - línea: 313
    - argumentos: j
- getWaTargets:
    - tipo: function
    - línea: 445
    - argumentos: mode, waLoc
- sendNow:
    - tipo: function
    - línea: 470
    - argumentos: (sin parámetros)
- initOnce:
    - tipo: function
    - línea: 627
    - argumentos: (sin parámetros)
- boot:
    - tipo: function
    - línea: 633
    - argumentos: (sin parámetros)

## API bases detectadas
- API_BASE = /meatze/v5
- API_N = API_BASE + '/notify'

## Endpoints detectados (literales)
- (ninguno detectado)

## Endpoints detectados (templates)
- (ninguno detectado)

## Endpoints detectados (partes / strings)
- /meatze/v5
- /notify

## Selectores DOM usados
- input[name="mzs-mode"]:checked
- input[name="mzs-mode"]
- input[name="mzs-mode"][value="selected"]
- #ui-subs

## Eventos registrados (addEventListener)
- click @ line 84
- change @ line 635
- change @ line 641
- change @ line 650
- click @ line 658
- input @ line 666
- input @ line 671
- change @ line 695
- click @ line 707
- click @ line 718
- click @ line 724
- click @ line 732
- click @ line 758
- click @ line 763
- click @ line 768
- click @ line 772
- mz:admin-auth @ line 801
- mz:pane:show @ line 805

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- fetch @ line 27: arg0=None
- addEventListener @ line 84: arg0=click
- fetch @ line 273: arg0={'__template': '`${API_N}/wa-import${qs()}`'}
- apiJSON @ line 303: arg0={'__template': '`${API_N}/subscribers${qs(true)}`'}
- apiJSON @ line 407: arg0={'__template': '`${API_N}/wa-toggle${qs()}`'}
- apiJSON @ line 416: arg0={'__template': '`${API_N}/wa-delete${qs()}`'}
- fetch @ line 537: arg0={'__template': '`${API_N}/upload-wa${qs()}`'}
- apiJSON @ line 586: arg0={'__template': '`${API_N}/broadcast${qs()}`'}
- addEventListener @ line 635: arg0=change
- addEventListener @ line 641: arg0=change
- addEventListener @ line 650: arg0=change
- addEventListener @ line 658: arg0=click
- addEventListener @ line 666: arg0=input
- addEventListener @ line 671: arg0=input
- addEventListener @ line 695: arg0=change
- addEventListener @ line 707: arg0=click
- addEventListener @ line 718: arg0=click
- addEventListener @ line 724: arg0=click
- apiJSON @ line 744: arg0={'__template': '`${API_N}/wa-upsert${qs()}`'}
- addEventListener @ line 732: arg0=click
- addEventListener @ line 758: arg0=click
- addEventListener @ line 763: arg0=click
- addEventListener @ line 768: arg0=click
- apiJSON @ line 777: arg0={'__template': '`${API_N}/wa-clear${qs()}`'}
- addEventListener @ line 772: arg0=click
- addEventListener @ line 801: arg0=mz:admin-auth
- addEventListener @ line 805: arg0=mz:pane:show

## Variables globales declaradas
- $
- WA_PAGE_SIZE
- waPage
- previewObjectUrl
- waSelectedManual
- cancelBroadcast
- subsCache
- API_BASE
- API_N
- tok
- qs
- auth
- apiJSON
- sleep
- renderSelectedRecipients
- addWaSelected
- syncPicked
- showProgress
- updateProgress
- hideProgress
- getPreviewName
- getCurrentFile
- applyWaSearchFilter
- updatePreview
- handleWaImport
- loadSubs
- drawSubs
- getWaTargets
- sendNow
- inited
- initOnce
- boot
