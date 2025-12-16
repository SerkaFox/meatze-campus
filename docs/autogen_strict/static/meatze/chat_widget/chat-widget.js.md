# Archivo: static/meatze/chat_widget/chat-widget.js

## Tipo de archivo
js

## Funciones
- $:
    - tipo: arrow
    - línea: 2
    - argumentos: s
- openChat:
    - tipo: function
    - línea: 17
    - argumentos: (sin parámetros)
- closeChat:
    - tipo: function
    - línea: 24
    - argumentos: (sin parámetros)
- escapeHTML:
    - tipo: function
    - línea: 38
    - argumentos: s
- linkifyPlainText:
    - tipo: function
    - línea: 47
    - argumentos: s
- walk:
    - tipo: arrow
    - línea: 72
    - argumentos: node
- sanitizeBotHTML:
    - tipo: function
    - línea: 65
    - argumentos: html
- formatBotMessage:
    - tipo: function
    - línea: 109
    - argumentos: text
- appendUser:
    - tipo: function
    - línea: 136
    - argumentos: text
- appendBot:
    - tipo: function
    - línea: 152
    - argumentos: name, avatar, text
- renderDuoAnswer:
    - tipo: function
    - línea: 178
    - argumentos: answer
- sendMsg:
    - tipo: function
    - línea: 200
    - argumentos: (sin parámetros)

## API bases detectadas
- AVA_ANA = /static/meatze/avatars/ana.png
- AVA_CARLOS = /static/meatze/avatars/carlos.png

## Endpoints detectados (literales)
- /meatze/v5/ai/help

## Endpoints detectados (templates)
- (ninguno detectado)

## Endpoints detectados (partes / strings)
- /static/meatze/avatars/ana.png
- /static/meatze/avatars/carlos.png
- /meatze/v5/ai/help

## Selectores DOM usados
- #mz-chat-fab
- #mz-chat-panel
- #mz-chat-close
- #mz-chat-backdrop
- #mz-chat-body
- #mz-chat-input
- #mz-chat-send

## Eventos registrados (addEventListener)
- click @ line 31
- click @ line 32
- click @ line 33
- keydown @ line 34
- click @ line 229
- keydown @ line 230

## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)
- addEventListener @ line 31: arg0=click
- addEventListener @ line 32: arg0=click
- addEventListener @ line 33: arg0=click
- addEventListener @ line 34: arg0=keydown
- fetch @ line 212: arg0=/meatze/v5/ai/help
- addEventListener @ line 229: arg0=click
- addEventListener @ line 230: arg0=keydown

## Variables globales declaradas
- $
- fab
- panel
- closeBtn
- backdrop
- body
- input
- send
- AVA_ANA
- AVA_CARLOS
- openChat
- closeChat
- escapeHTML
- linkifyPlainText
- sanitizeBotHTML
- formatBotMessage
- appendUser
- appendBot
- renderDuoAnswer
- sendMsg
