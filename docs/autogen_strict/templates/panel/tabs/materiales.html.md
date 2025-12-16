# Archivo: templates/panel/tabs/materiales.html

## Tipo de archivo
html

## IDs de elementos
- mz-upl-add
- mz-upl-rows
- mzf-send
- {{ f.id }}

## Clases CSS usadas
- %}
- 'none'
- ==
- audience
- endif
- ghost
- ghost{%
- if
- is-act{%
- key
- m.name
- muted
- mz-chip-mini
- mz-file-clear
- mz-mat-actions
- mz-mat-audience
- mz-mat-card
- mz-mat-count
- mz-mat-dot
- mz-mat-head
- mz-mat-item
- mz-mat-list
- mz-mat-main
- mz-mat-meta
- mz-mat-modfilters
- mz-mat-sub
- mz-mat-tag
- mz-mat-title
- mz-mat-title-file
- mz-pill{%
- mz-seg
- mz-upl
- mz-upl-input
- mz-upl-remove-row
- mz-upl-row
- mz-upl-rows
- mz-upl-select
- mz-upl-wrap
- mzc-btn
- mzc-card
- mzc-note
- not
- selected_mod

## Formularios detectados (<form>)
- <form method="post" enctype="multipart/form-data" class="mz-upl"
      data-action="materials.upload.form">
- <form method="post" style="margin:0">
- <form method="post" style="margin:0">
- <form method="post" style="margin:0"
                    onsubmit="return confirm('¿Eliminar este archivo?');">

## Bloques de plantilla ({% block %})
- (ninguno detectado)

## Includes de plantilla ({% include %})
- (ninguno detectado)

## Variables de plantilla ({{ ... }})
- files|length
- files|length|pluralize:"s"
- key
- key
- label
- audience
- total_files
- audience
- none_count
- audience
- m.name|urlencode
- m.name
- m.name
- m.count
- name|default_if_none:''
- name
- f.file.url
- f.id
- f.title|default:f.filename
- f.ext|upper
- f.fmt_size
- f.uploaded_by.get_full_name|default:f.uploaded_by.email
- f.module_key
- f.id
- f.id
- f.id
- f.id
- f.id
