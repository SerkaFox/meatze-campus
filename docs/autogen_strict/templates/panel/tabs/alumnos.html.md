# Archivo: templates/panel/tabs/alumnos.html

## Tipo de archivo
html

## IDs de elementos
- mz-alumnos-tab
- mz-temp-count
- mz-temp-dl
- mz-temp-gen
- mz-temp-msg
- mz-temp-present
- mz-temp-present-overlay
- mz-temp-root
- mz-temp-rot
- mz-temp-sel
- mz-temp-table
- mz-tp-close
- {{ s.id }}

## Clases CSS usadas
- ghost
- mz-alu-actions
- mz-alu-badge
- mz-alu-head
- mz-alu-inline-pass
- mz-alu-sub
- mz-alu-tablewrap
- mz-alu-title
- mz-copy
- mz-inline-pass
- mz-pass-copy
- mz-tbl
- mz-temp-bar
- mz-temp-input
- mz-temp-present-wrap
- mz-temp-select
- mzc-btn
- mzc-card
- mzc-h2
- mzc-inp
- mzc-note
- sm

## Formularios detectados (<form>)
- <form method="post" style="margin:0">
- <form method="post" style="margin:0"
                          onsubmit="return confirm('¿Eliminar a este alumno del curso?');">

## Bloques de plantilla ({% block %})
- (ninguno detectado)

## Includes de plantilla ({% include %})
- (ninguno detectado)

## Variables de plantilla ({{ ... }})
- students|length
- students|length|pluralize:"s"
- s.idx
- s.name
- s.email
- s.id
- s.id
- s.id
- s.id
- s.last_pass
- s.last_pass
- s.id
- curso.codigo
