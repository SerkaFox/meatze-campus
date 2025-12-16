# Archivo: static/meatze/admin/wa.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 4
    - argumentos: s, root=...
- tok:
    - tipo: arrow
    - línea: 19
    - argumentos: (sin parámetros)
- qs:
    - tipo: arrow
    - línea: 20
    - argumentos: bust=...
- auth:
    - tipo: arrow
    - línea: 21
    - argumentos: isPost=...
- apiJSON:
    - tipo: function
    - línea: 27
    - argumentos: url, opt=...
- showNewMsgToast:
    - tipo: function
    - línea: 37
    - argumentos: from, text
- getRowLoc:
    - tipo: function
    - línea: 52
    - argumentos: row
- loadInbox:
    - tipo: function
    - línea: 59
    - argumentos: (sin parámetros)
- autoRefreshInbox:
    - tipo: function
    - línea: 96
    - argumentos: (sin parámetros)
- buildThreadItem:
    - tipo: function
    - línea: 123
    - argumentos: t, activeShort
- renderInboxThreadList:
    - tipo: function
    - línea: 194
    - argumentos: (sin parámetros)
- highlightActiveThread:
    - tipo: function
    - línea: 260
    - argumentos: wa
- openChat:
    - tipo: function
    - línea: 270
    - argumentos: wa, name
- closeChat:
    - tipo: function
    - línea: 300
    - argumentos: (sin parámetros)
- renderChatLog:
    - tipo: function
    - línea: 309
    - argumentos: wa
- sendChatReply:
    - tipo: function
    - línea: 366
    - argumentos: (sin parámetros)
- initOnce:
    - tipo: function
    - línea: 413
    - argumentos: (sin parámetros)
- boot:
    - tipo: function
    - línea: 419
    - argumentos: (sin parámetros)

## API bases detectadas
- API_BASE = /meatze/v5
- API_N = API_BASE + '/notify'
- notifyAudio = new Audio(
	  window.MZ_NOTIFY_URL || '/static/files/meatze_notify.mp3'
	)

## Endpoints detectados (literales)
- (ninguno detectado)

## Endpoints detectados (templates)
- (ninguno detectado)

## Endpoints detectados (partes / strings)
- /static/files/meatze_notify.mp3
- /meatze/v5
- /notify
- https://meatze.eus/wp-content/uploads/2024/11/meatze-icon.png

## Selectores DOM usados
- [data-thread-wa]
- #ui-wa

## Eventos registrados (addEventListener)
- click @ line 171
- click @ line 175
- change @ line 423
- click @ line 426
- click @ line 431
- click @ line 432
- mz:admin-auth @ line 443
- mz:pane:show @ line 447

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- fetch @ line 28: arg0=None
- apiJSON @ line 69: arg0=None
- apiJSON @ line 99: arg0=None
- addEventListener @ line 171: arg0=click
- apiJSON @ line 179: arg0={'__template': '`${API_N}/wa-inbox-delete${qs()}`'}
- addEventListener @ line 175: arg0=click
- apiJSON @ line 384: arg0={'__template': '`${API_N}/wa-reply${qs()}`'}
- addEventListener @ line 423: arg0=change
- addEventListener @ line 426: arg0=click
- addEventListener @ line 431: arg0=click
- addEventListener @ line 432: arg0=click
- addEventListener @ line 443: arg0=mz:admin-auth
- addEventListener @ line 447: arg0=mz:pane:show

## Variables globales declaradas
- $
- inboxCache
- currentChatWa
- lastInboxIds
- newMsgThreads
- autoTimer
- notifyAudio
- API_BASE
- API_N
- tok
- qs
- auth
- apiJSON
- showNewMsgToast
- getRowLoc
- loadInbox
- autoRefreshInbox
- buildThreadItem
- renderInboxThreadList
- highlightActiveThread
- openChat
- closeChat
- renderChatLog
- sendChatReply
- inited
- initOnce
- boot
