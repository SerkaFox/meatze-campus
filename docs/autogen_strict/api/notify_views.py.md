# Archivo: api/notify_views.py

## Tipo de archivo
python

## Funciones
- normalize_wa:
    - tipo: function
    - línea: 36
    - argumentos: raw
- _admin_ok:
    - tipo: function
    - línea: 61
    - argumentos: request
- _require_admin:
    - tipo: function
    - línea: 72
    - argumentos: request
- wa_msisdn:
    - tipo: function
    - línea: 83
    - argumentos: num
- wa_api:
    - tipo: function
    - línea: 100
    - argumentos: path, body
- wa_send_text:
    - tipo: function
    - línea: 136
    - argumentos: to, text
- wa_send_document:
    - tipo: function
    - línea: 157
    - argumentos: to, doc_url, filename
- wa_send_template:
    - tipo: function
    - línea: 178
    - argumentos: to, tpl_name, body_params, header_media, lang
- wa_send_hello_world:
    - tipo: function
    - línea: 241
    - argumentos: to
- wa_send_broadcast_simple:
    - tipo: function
    - línea: 245
    - argumentos: to, text
- wa_send_personal_txt:
    - tipo: function
    - línea: 253
    - argumentos: to, name, text
- wa_send_personal_document:
    - tipo: function
    - línea: 258
    - argumentos: to, name, text, doc_url, filename
- wa_send_personal_photo:
    - tipo: function
    - línea: 272
    - argumentos: to, name, text, img_url
- store_inbox:
    - tipo: function
    - línea: 282
    - argumentos: wa, name, msg, source, direction
- subscribers:
    - tipo: function
    - línea: 304
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- wa_upsert:
    - tipo: function
    - línea: 327
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- wa_delete:
    - tipo: function
    - línea: 364
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- wa_toggle:
    - tipo: function
    - línea: 385
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- wa_import:
    - tipo: function
    - línea: 419
    - argumentos: request
    - decoradores: api_view, authentication_classes, permission_classes
- upload_wa:
    - tipo: function
    - línea: 577
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- broadcast:
    - tipo: function
    - línea: 603
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- ws_webhook:
    - tipo: function
    - línea: 719
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes
- wa_clear:
    - tipo: function
    - línea: 804
    - argumentos: request
    - decoradores: api_view, authentication_classes, permission_classes
- wa_inbox:
    - tipo: function
    - línea: 821
    - argumentos: request
    - decoradores: api_view, authentication_classes, permission_classes
- wa_inbox_delete:
    - tipo: function
    - línea: 864
    - argumentos: request
    - decoradores: api_view, authentication_classes, permission_classes
- wa_reply:
    - tipo: function
    - línea: 884
    - argumentos: request
    - decoradores: api_view, authentication_classes, permission_classes
- ai_portal_helper:
    - tipo: function
    - línea: 937
    - argumentos: request
    - decoradores: api_view, permission_classes, authentication_classes

## Clases
- (ninguna detectada)

## Endpoints detectados (strings)
- 
    GET /meatze/v5/notify/subscribers
    Возвращает словарь wa -> {name, loc, active}, как в WP.
    
- 
    GET /meatze/v5/notify/wa-inbox?limit=50
    Отдаём последние N сообщений для панели чата.
    Формат под wa.js: { items: [ {id, wa, msg, created_at, wa_name, sub_name, loc, direction}, ... ] }
    
- 
    POST /meatze/v5/ai/portal_helper
    { "question": "...", "history": [ { "role": "user"|"assistant", "content": "..." }, ... ] }
    
- 
    POST /meatze/v5/notify/broadcast
    Тело максимально похоже на WP /news/broadcast, но реализуем только канал 'wa'.

    Важные поля:
      - mode: "all" | "selected"
      - channels: ["wa"]
      - text: текст рассылки
      - sel_wa: ["600...", "699..."] (для mode=selected)
      - test_wa: "600..." — если есть, шлём только ему
      - wa_tpl: "personal_txt" | "personal_photo" | "personal_doc" | "hello_world" | "broadcast"
      - wa_media_url, wa_media_name
      - wa_loc: "Bilbao" | "Barakaldo" | ""
    
- 
    POST /meatze/v5/notify/upload-wa
    form-data: file
    Возвращает url + filename, как WP upload-wa.
    
- 
    POST /meatze/v5/notify/wa-clear
    Полностью очищает таблицу WhatsApp-контактов.
    
- 
    POST /meatze/v5/notify/wa-delete
    { "wa": "600123123" }
    
- 
    POST /meatze/v5/notify/wa-import
    form-data: file (CSV/XLSX), loc (Bilbao|Barakaldo|'')
    
- 
    POST /meatze/v5/notify/wa-inbox-delete
    { "wa": "600123123" }
    
- 
    POST /meatze/v5/notify/wa-reply
    { "wa": "600123123", "text": "..." }
    Отправляет текст в WhatsApp и пишет запись в WaInbox (direction='out').
    
- 
    POST /meatze/v5/notify/wa-toggle
    — меняет active 0/1
    
- 
    POST /meatze/v5/notify/wa-upsert
    Тело: { wa, name, loc, active }
    
- /messages
