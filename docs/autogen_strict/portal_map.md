# Portal Map (strict, desde facts.jsonl)

## admin:base_admin

### Templates
- templates/meatze_admin/base_admin.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 6
  - adm-enter-shared
  - adm-eye-shared
  - adm-gate-msg
  - adm-pass-shared
  - adm-pills
  - adm-shared-gate
- classes: 9
  - mz-btn
  - mz-card
  - mz-eye-btn
  - mz-eye-wrap
  - mz-help
  - mz-inp
  - mz-page
  - pill
  - pillbar

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## admin:cursos

### Templates
- templates/meatze_admin/cursos.html

### Scripts
- static/meatze/admin/cursos.js

### UI (HTML)
- ids: 21
  - mzc-ca-assign
  - mzc-ca-assigned
  - mzc-ca-codigo
  - mzc-ca-curso
  - mzc-ca-msg
  - mzc-ca-reload
  - mzc-ca-teachers-chips
  - mzc-cf-clear
  - mzc-cf-codigo
  - mzc-cf-list
  - mzc-cf-modulos
  - mzc-cf-msg
  - mzc-cf-save
  - mzc-cf-titulo
  - mzc-cf-total-horas
  - mzc-cf-total-modulos
  - mzc-pane-assign
  - mzc-pane-form
  - mzc-tab-assign
  - mzc-tab-form
  - ui-cursos
- classes: 12
  - cols-2
  - hub
  - link
  - mz-btn
  - mz-card
  - mz-chipbox
  - mz-help
  - mz-inp
  - mz-pane
  - mz-row
  - mz-sel
  - mz-table

### JS (facts)
- apiBases:
  - API_A = API_BASE + '/admin'
  - API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5'
- endpoints (literales): 0
- endpoints (templates): 5
  - `${API_A}/cursos/upsert${qs()}`
  - `${API_A}/cursos${qs(true)}`
  - `${API_A}/cursos/${it.id}/delete${qs()}`
  - `${API_A}/teachers${qs(true)}`
  - `${API_A}/cursos/assign${qs()}`
- endpoints (parts): 3
  - /
  - /meatze/v5
  - /admin
- domSelectors: 21
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
- events: 10
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
- functions: 18
  - $, tok, qs, auth, apiJSON, toModulesArray, esc, normId, parseModulesBasic, updateCounters, setTab, loadList, buildTeacherChips, getSelectedTeacherIdsFromChips, renderAssignedBadges, loadAssignForm, updateAssignedTeachers, initCursosOnce

## admin:horarios

### Templates
- templates/meatze_admin/horarios.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 51
  - mzh-alumno
  - mzh-alumno-wrap
  - mzh-auto-aula
  - mzh-auto-desde
  - mzh-auto-end
  - mzh-auto-end-wrap
  - mzh-auto-hasta
  - mzh-auto-horas
  - mzh-auto-horas-wrap
  - mzh-auto-msg
  - mzh-auto-nota
  - mzh-auto-nota-wrap
  - mzh-auto-panel
  - mzh-auto-run
  - mzh-auto-skiphol
  - mzh-auto-start
  - mzh-busy
  - mzh-busybar
  - mzh-busytxt
  - mzh-ctx
  - mzh-curso
  - mzh-dow-1
  - mzh-dow-2
  - mzh-dow-3
  - mzh-dow-4
  - mzh-dow-5
  - mzh-dow-6
  - mzh-dow-7
  - mzh-export-graphic
  - mzh-firstday-desde
  - mzh-firstday-hasta
  - mzh-firstday-special
  - mzh-firstday-wrap
  - mzh-fixed-msg
  - mzh-fixed-panel
  - mzh-fixed-save
  - mzh-fixed-toggle
  - mzh-fixed-y1
  - mzh-fixed-y1-label
  - mzh-fixed-y2
  - mzh-fixed-y2-label
  - mzh-grid
  - mzh-hol-list
  - mzh-hol-stats
  - mzh-legend
  - mzh-next
  - mzh-prev
  - mzh-selcnt
  - mzh-tipo
  - mzh-title
  - ui-horarios
- classes: 33
  - busy-bar
  - busy-mask
  - busy-panel
  - cal-head
  - dow
  - grid
  - legend
  - link
  - mz-auto-aula
  - mz-auto-card
  - mz-auto-dow
  - mz-auto-dow-list
  - mz-auto-flag
  - mz-auto-flags
  - mz-auto-footer
  - mz-auto-grid
  - mz-auto-head
  - mz-auto-info
  - mz-auto-panel
  - mz-auto-range
  - mz-auto-range-sep
  - mz-btn
  - mz-card
  - mz-editor-title
  - mz-fixed-actions
  - mz-fixed-card
  - mz-help
  - mz-inp
  - mz-pane
  - mz-row
  - mz-sel
  - primary
  - title

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## admin:subs

### Templates
- templates/meatze_admin/subs.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 36
  - mzs-counts
  - mzs-filter-loc
  - mzs-msg
  - mzs-picked
  - mzs-picked-list
  - mzs-preview-card
  - mzs-preview-media
  - mzs-preview-text
  - mzs-progress
  - mzs-progress-cancel
  - mzs-progress-sub
  - mzs-progress-text
  - mzs-refresh
  - mzs-sel-wa
  - mzs-send
  - mzs-text
  - mzs-wa-body
  - mzs-wa-clear
  - mzs-wa-edit-active
  - mzs-wa-edit-loc
  - mzs-wa-edit-name
  - mzs-wa-edit-num
  - mzs-wa-edit-save
  - mzs-wa-file
  - mzs-wa-file-clear
  - mzs-wa-file-help
  - mzs-wa-file-name
  - mzs-wa-import-file
  - mzs-wa-import-loc
  - mzs-wa-import-msg
  - mzs-wa-import-run
  - mzs-wa-next
  - mzs-wa-page-info
  - mzs-wa-prev
  - mzs-wa-search
  - ui-subs
- classes: 12
  - danger
  - link
  - mz-btn
  - mz-card
  - mz-help
  - mz-inp
  - mz-pane
  - mz-row
  - mz-sec
  - mz-sel
  - mz-table
  - sm

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## admin:teachers

### Templates
- templates/meatze_admin/teachers.html

### Scripts
- static/meatze/admin/teachers.js

### UI (HTML)
- ids: 15
  - mzp-body
  - mzp-clear
  - mzp-refresh
  - mzp-search
  - mzt-bio
  - mzt-body
  - mzt-clear
  - mzt-email
  - mzt-first
  - mzt-last1
  - mzt-last2
  - mzt-msg
  - mzt-save
  - mzt-search
  - ui-teachers
- classes: 9
  - cols-4
  - link
  - mz-btn
  - mz-card
  - mz-help
  - mz-inp
  - mz-pane
  - mz-row
  - mz-table

### JS (facts)
- apiBases:
  - API_A = API_BASE + '/admin'
  - API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5'
- endpoints (literales): 0
- endpoints (templates): 4
  - `${API_A}/teachers${qs(true)}`
  - `${API_A}/teachers/${it.id}${qs()}`
  - `${API_A}/teachers/${id}/delete${qs()}`
  - `${API_A}/teachers${qs()}`
- endpoints (parts): 4
  - /
  - /meatze/v5
  - /admin
  - /admin/pending
- domSelectors: 15
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
- events: 8
  - click @ line 115
  - click @ line 116
  - input @ line 117
  - input @ line 210
  - click @ line 211
  - click @ line 214
  - mz:admin-auth @ line 245
  - mz:pane:show @ line 248
- functions: 20
  - $, tok, qs, auth, apiJSON, esc, escAttr, nrm, debounce, refreshPending, pendingRow, drawPending, applyPendingFilter, refreshList, rowView, rowEdit, doDelete, drawRows, applyFilter, initTeachersOnce

## admin:wa

### Templates
- templates/meatze_admin/wa.html

### Scripts
- static/meatze/admin/wa.js

### UI (HTML)
- ids: 12
  - mzi-chat
  - mzi-chat-close
  - mzi-chat-empty
  - mzi-chat-input
  - mzi-chat-log
  - mzi-chat-msg
  - mzi-chat-send
  - mzi-chat-title
  - mzi-refresh
  - mzi-src
  - mzi-thread-list
  - ui-wa
- classes: 8
  - link
  - mz-btn
  - mz-card
  - mz-help
  - mz-inp
  - mz-pane
  - mz-sel
  - sm

### JS (facts)
- apiBases:
  - API_BASE = /meatze/v5
  - API_N = API_BASE + '/notify'
  - notifyAudio = new Audio(
	  window.MZ_NOTIFY_URL || '/static/files/meatze_notify.mp3'
	)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 4
  - /static/files/meatze_notify.mp3
  - /meatze/v5
  - /notify
  - https://meatze.eus/wp-content/uploads/2024/11/meatze-icon.png
- domSelectors: 2
  - [data-thread-wa]
  - #ui-wa
- events: 8
  - click @ line 171
  - click @ line 175
  - change @ line 423
  - click @ line 426
  - click @ line 431
  - click @ line 432
  - mz:admin-auth @ line 443
  - mz:pane:show @ line 447
- functions: 18
  - $, tok, qs, auth, apiJSON, showNewMsgToast, getRowLoc, loadInbox, autoRefreshInbox, buildThreadItem, renderInboxThreadList, highlightActiveThread, openChat, closeChat, renderChatLog, sendChatReply, initOnce, boot

## js:chat-widget

### Templates
- (ninguno)

### Scripts
- static/meatze/chat_widget/chat-widget.js

### UI (HTML)
- ids: 0
- classes: 0

### JS (facts)
- apiBases:
  - AVA_ANA = /static/meatze/avatars/ana.png
  - AVA_CARLOS = /static/meatze/avatars/carlos.png
- endpoints (literales): 1
  - /meatze/v5/ai/help
- endpoints (templates): 0
- endpoints (parts): 3
  - /static/meatze/avatars/ana.png
  - /static/meatze/avatars/carlos.png
  - /meatze/v5/ai/help
- domSelectors: 7
  - #mz-chat-fab
  - #mz-chat-panel
  - #mz-chat-close
  - #mz-chat-backdrop
  - #mz-chat-body
  - #mz-chat-input
  - #mz-chat-send
- events: 6
  - click @ line 31
  - click @ line 32
  - click @ line 33
  - keydown @ line 34
  - click @ line 229
  - keydown @ line 230
- functions: 12
  - $, openChat, closeChat, escapeHTML, linkifyPlainText, walk, sanitizeBotHTML, formatBotMessage, appendUser, appendBot, renderDuoAnswer, sendMsg

## panel:alumno_home

### Templates
- templates/panel/alumno_home.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 0
- classes: 8
  - mz-course
  - mz-empty
  - mz-empty-hint
  - mz-grid
  - mz-wrap
  - mzc-card
  - mzc-note
  - mzc-title

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:alumnos

### Templates
- templates/panel/tabs/alumnos.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 13
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
- classes: 22
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

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:calendario

### Templates
- templates/panel/tabs/calendario.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 9
  - mc-scope-curso
  - mc-scope-prac
  - mcal-day
  - mcal-dow
  - mcal-grid
  - mcal-legend
  - mcal-next
  - mcal-prev
  - mzt-cal
- classes: 14
  - ghost
  - mz-seg
  - mzc-btn
  - mzc-cal
  - mzc-calHead
  - mzc-card
  - mzc-chip
  - mzc-day
  - mzc-dot
  - mzc-grid7
  - mzc-leg
  - mzc-legItem
  - mzc-muted
  - mzc-note

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:chat

### Templates
- templates/panel/tabs/chat.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 13
  - ${id}
  - ${m.id}
  - ${mid}
  - ${msgId}
  - ${msg}
  - mz-attach
  - mz-chat-root
  - mz-emoji
  - mz-send
  - mzcl
  - mzcu-unread
  - mzf
  - mzi
- classes: 40
  - ${self
  - ''}
  - 'me'
  - :
  - ?
  - cnt
  - emo
  - ghost
  - itm
  - mz-avatar
  - mz-bubble
  - mz-chat
  - mz-chat-head
  - mz-chat-hint
  - mz-chat-list
  - mz-chat-shell
  - mz-chat-title
  - mz-chat-unread
  - mz-chip
  - mz-chip${mine}
  - mz-chips
  - mz-emoji
  - mz-file
  - mz-input
  - mz-input-btn
  - mz-input-send
  - mz-input-text
  - mz-meta
  - mz-msg
  - mz-msg-del
  - mz-msg-new
  - mz-react-btn
  - mz-reactions
  - mz-tab-badge
  - mz-tab-dot
  - mz-text
  - mzc-btn
  - mzc-inp
  - mzc-note
  - mzc-title

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:course_panel

### Templates
- templates/panel/course_panel.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 4
  - mz-panel
  - mz-panel-overlay
  - mz-panel-wrap
  - mzp-body
- classes: 17
  - %}
  - ==
  - active_tab
  - dot
  - endif
  - ghost{%
  - if
  - is-act{%
  - m.slug
  - mz-tabs
  - mzc-btn
  - mzc-card
  - mzc-head
  - mzc-note
  - mzc-tab-inner
  - mzc-title
  - mzc-wrap

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:ia

### Templates
- templates/panel/tabs/ia.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 19
  - mzt-ai
  - mzt-ai-present-close
  - mzt-ai-present-copy
  - mzt-ai-present-overlay
  - mzt-copy
  - mzt-full
  - mzt-full-close
  - mzt-full-content
  - mzt-full-copy
  - mzt-fullscreen
  - mzt-input
  - mzt-module
  - mzt-out
  - mzt-presets
  - mzt-send
  - mzt-status
  - mzt-toast
  - mzt-topic
  - mzt-use-course
- classes: 38
  - close
  - ghost
  - is-act
  - mz-seg
  - mzc-btn
  - mzc-card
  - mzc-h2
  - mzc-inp
  - mzc-note
  - mzt-ai-btn
  - mzt-checkbox
  - mzt-field
  - mzt-footer
  - mzt-full-actions
  - mzt-full-content
  - mzt-full-head
  - mzt-full-inner
  - mzt-fullscreen
  - mzt-input-card
  - mzt-label
  - mzt-levels
  - mzt-lvl
  - mzt-main-btn
  - mzt-out
  - mzt-output-actions
  - mzt-output-card
  - mzt-output-head
  - mzt-output-title
  - mzt-presets
  - mzt-presets-label
  - mzt-presets-wrap
  - mzt-row
  - mzt-row-level
  - mzt-row-topic
  - mzt-sm-btn
  - mzt-status
  - mzt-textarea
  - mzt-toast

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:info

### Templates
- templates/panel/tabs/info.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 0
- classes: 15
  - mz-info-card
  - mz-info-chip
  - mz-info-head
  - mz-info-label
  - mz-info-line
  - mz-info-meta
  - mz-info-mod-hours
  - mz-info-mod-item
  - mz-info-mod-name
  - mz-info-mods
  - mz-info-mods-head
  - mz-info-mods-list
  - mz-info-mods-title
  - mz-info-title
  - mz-info-value

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## panel:materiales

### Templates
- templates/panel/tabs/materiales.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 4
  - mz-upl-add
  - mz-upl-rows
  - mzf-send
  - {{ f.id }}
- classes: 43
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

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## tpl:base

### Templates
- templates/base.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 59
  - ack-saved
  - auth-email
  - auth-pass
  - auth-pass-login
  - auth-pin
  - auto-login-msg
  - btn-done
  - btn-login-pass
  - btn-open-temp
  - btn-resend
  - btn-send-pin
  - btn-setpass
  - btn-temp-back
  - btn-temp-cancel
  - btn-temp-check
  - btn-temp-enter
  - btn-temp-finish
  - btn-verify
  - msg-pass-login
  - msg-pin
  - msg-setpass
  - msg-temp
  - msg-temp-finish
  - mz-acc
  - mz-acc-menu
  - mz-acc-user
  - mz-auth
  - mz-auth-close
  - mz-auth-ov
  - mz-auth-title
  - mz-btn-login
  - mz-prof
  - mz-prof-bio
  - mz-prof-cancel
  - mz-prof-close
  - mz-prof-display
  - mz-prof-first
  - mz-prof-last1
  - mz-prof-last2
  - mz-prof-msg
  - mz-prof-ov
  - mz-prof-pass-msg
  - mz-prof-pass1
  - mz-prof-pass2
  - mz-prof-save
  - mz-prof-title
  - mz-top
  - new-email-display
  - new-pass-display
  - pin-wrap
  - step-email
  - step-setpass
  - step-temp
  - step-temp-finish
  - temp-code
  - temp-course
  - temp-fullname
  - temp-name
  - temp-pass
- classes: 34
  - ghost
  - icon
  - link
  - mz-acc
  - mz-acc-arrow
  - mz-acc-avatar
  - mz-acc-item
  - mz-acc-menu
  - mz-acc-name
  - mz-auth-actions
  - mz-auth-b
  - mz-auth-h
  - mz-auth-title
  - mz-brand
  - mz-brand-badge
  - mz-btn
  - mz-btn-top
  - mz-copy
  - mz-field
  - mz-grid2
  - mz-help
  - mz-inp
  - mz-label
  - mz-ok
  - mz-page
  - mz-prof-b
  - mz-prof-h
  - mz-prof-title
  - mz-reveal
  - mz-top-cta
  - mz-top-inner
  - mz-top-right
  - mz-x
  - sm

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## tpl:chat_widget

### Templates
- templates/includes/chat_widget.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 7
  - mz-chat-backdrop
  - mz-chat-body
  - mz-chat-close
  - mz-chat-fab
  - mz-chat-input
  - mz-chat-panel
  - mz-chat-send
- classes: 15
  - mz-chat-avatars
  - mz-chat-backdrop
  - mz-chat-body
  - mz-chat-foot
  - mz-chat-h1
  - mz-chat-h2
  - mz-chat-head
  - mz-chat-input
  - mz-chat-panel
  - mz-chat-send
  - mz-chat-title
  - mz-chat-x
  - mz-fab
  - mz-fab-dot
  - mz-fab-ico

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0

## tpl:home

### Templates
- templates/home.html

### Scripts
- (ninguno)

### UI (HTML)
- ids: 4
  - mz-ai-footnote
  - mz-ai-input
  - mz-ai-log
  - mz-ai-send
- classes: 25
  - mz-ai-avatar
  - mz-ai-avatar-inner
  - mz-ai-badge
  - mz-ai-card
  - mz-ai-foot
  - mz-ai-head
  - mz-ai-head-txt
  - mz-ai-input
  - mz-ai-input-row
  - mz-ai-log
  - mz-ai-send
  - mz-ai-status
  - mz-ai-tags
  - mz-chip-tag
  - mz-dot
  - mz-hero-card
  - mz-hero-cta
  - mz-hero-feats
  - mz-hero-footer
  - mz-hero-note
  - mz-hero-pill
  - mz-hero-sub
  - mz-hero-title
  - mz-home-grid
  - mz-home-wrap

### JS (facts)
- apiBases: (ninguna)
- endpoints (literales): 0
- endpoints (templates): 0
- endpoints (parts): 0
- domSelectors: 0
- events: 0
- functions: 0


## Unmapped

- html: 0
- js: 0
- python: 8
  - api/models.py
  - api/urls.py
  - api/views.py
  - api/auth_views.py
  - api/views_temp.py
  - api/views_ai.py
  - meatze_site/urls.py
  - meatze_site/settings.py
- other: 0
