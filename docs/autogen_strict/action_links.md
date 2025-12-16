# Action Links (strict, extracted from JS AST)

## static/meatze/admin/admin-core.js

- **DOMContentLoaded** on `(unknown selector)` (line 157)
  - handlerName: `initPanelsOnce`
- **click** on `(unknown selector)` (line 34)
  - calls: $
- **click** on `(unknown selector)` (line 71)
  - calls: $, trim, tryTokenShared
- **click** on `(unknown selector)` (line 142)
  - calls: showPanel
- **keydown** on `(unknown selector)` (line 83)
  - calls: preventDefault, $, click

## static/meatze/admin/cursos.js

- **change** on `(unknown selector)` (line 414)
  - handlerName: `updateAssignedTeachers`
- **click** on `(unknown selector)` (line 357)
  - calls: getAttribute, setAttribute
- **input** on `(unknown selector)` (line 165)
  - handlerName: `updateCounters`
- **mz:admin-auth** on `(unknown selector)` (line 443)
  - calls: initCursosOnce
- **paste** on `(unknown selector)` (line 166)
  - calls: setTimeout
- **click** on `#mzc-ca-assign` (line 421)
  - calls: trim, getSelectedTeacherIdsFromChips, qs, auth, stringify, apiJSON, updateAssignedTeachers
- **click** on `#mzc-ca-reload` (line 415)
  - calls: loadAssignForm, updateAssignedTeachers
- **mz:pane:show** on `#ui-cursos` (line 446)
  - calls: initCursosOnce

## static/meatze/admin/horarios.js

- **(unknown event)** on `(unknown selector)` (line 585)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 586)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 587)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 588)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 591)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 592)
  - handlerName: `updateAutoPreview`
- **(unknown event)** on `(unknown selector)` (line 595)
  - handlerName: `updateAutoPreview`
- **change** on `(unknown selector)` (line 439)
  - calls: clearGrid, get, openCurso
- **change** on `(unknown selector)` (line 461)
  - handlerName: `recalcHorasFromEnd`
- **change** on `(unknown selector)` (line 466)
  - calls: updateAmbitoUI, clear, loadAlumnosForCurso, autoJumpToFirstDate, renderMonth
- **change** on `(unknown selector)` (line 481)
  - calls: clear, renderMonth, autoJumpToFirstDate
- **change** on `(unknown selector)` (line 569)
  - calls: loadHolidaysAndRenderList, updateAutoPreview
- **change** on `(unknown selector)` (line 576)
  - calls: updateAutoPreview
- **click** on `(unknown selector)` (line 493)
  - calls: getFullYear, getMonth, renderMonth
- **click** on `(unknown selector)` (line 498)
  - calls: getFullYear, getMonth, renderMonth
- **click** on `(unknown selector)` (line 503)
  - handlerName: `exportWordGraphicAll`
- **click** on `(unknown selector)` (line 507)
  - calls: getFullYear, loadFixedNonlective, String, split, map, compressDateList
- **click** on `(unknown selector)` (line 544)
  - calls: getFullYear, parseYearFieldExpanded, String, join, saveFixedNonlective, updateAutoPreview
- **click** on `(unknown selector)` (line 599)
  - handlerName: `autofillByModules`
- **input** on `(unknown selector)` (line 452)
  - calls: updateAutoPreview
- **mz:admin-auth** on `(unknown selector)` (line 1852)
  - calls: initOnce
- **mz:cursos-updated** on `(unknown selector)` (line 631)
  - calls: loadCursos, has, get, openCurso
- **pointerdown** on `(unknown selector)` (line 839)
  - calls: preventDefault, selectRange, has, toggleCell
- **pointerenter** on `(unknown selector)` (line 847)
  - calls: toggleCell
- **pointerup** on `(unknown selector)` (line 854)
- **mz:pane:show** on `#ui-horarios` (line 1855)
  - calls: initOnce

## static/meatze/admin/subs.js

- **change** on `(unknown selector)` (line 635)
  - handlerName: `syncPicked`
- **change** on `(unknown selector)` (line 641)
  - calls: drawSubs, updatePreview
- **change** on `(unknown selector)` (line 650)
  - calls: from, addWaSelected, forEach
- **change** on `(unknown selector)` (line 695)
  - calls: updatePreview
- **click** on `(unknown selector)` (line 84)
  - calls: delete, $, from, forEach, renderSelectedRecipients, updatePreview
- **click** on `(unknown selector)` (line 658)
  - calls: updateProgress
- **click** on `(unknown selector)` (line 707)
  - calls: updatePreview
- **click** on `(unknown selector)` (line 718)
  - calls: drawSubs
- **click** on `(unknown selector)` (line 724)
  - calls: drawSubs
- **click** on `(unknown selector)` (line 732)
  - calls: $, trim, alert, qs, auth, stringify, apiJSON, loadSubs
- **click** on `(unknown selector)` (line 758)
  - handlerName: `handleWaImport`
- **click** on `(unknown selector)` (line 763)
  - handlerName: `sendNow`
- **click** on `(unknown selector)` (line 768)
  - handlerName: `loadSubs`
- **click** on `(unknown selector)` (line 772)
  - calls: confirm, qs, auth, stringify, apiJSON, clear, loadSubs, alert
- **input** on `(unknown selector)` (line 666)
  - handlerName: `updatePreview`
- **input** on `(unknown selector)` (line 671)
  - calls: querySelector, syncPicked, applyWaSearchFilter, drawSubs
- **mz:admin-auth** on `(unknown selector)` (line 801)
  - calls: initOnce
- **mz:pane:show** on `#ui-subs` (line 805)
  - calls: initOnce

## static/meatze/admin/teachers.js

- **click** on `(unknown selector)` (line 115)
  - handlerName: `refreshPending`
- **click** on `(unknown selector)` (line 116)
  - calls: applyPendingFilter, focus
- **click** on `(unknown selector)` (line 211)
  - calls: applyFilter, focus
- **input** on `(unknown selector)` (line 117)
- **input** on `(unknown selector)` (line 210)
- **mz:admin-auth** on `(unknown selector)` (line 245)
  - calls: initTeachersOnce
- **click** on `#mzt-save` (line 214)
  - calls: $, trim, toLowerCase, test, qs, auth, stringify, apiJSON, refreshList
- **mz:pane:show** on `#ui-teachers` (line 248)
  - calls: initTeachersOnce

## static/meatze/admin/wa.js

- **change** on `(unknown selector)` (line 423)
  - handlerName: `renderInboxThreadList`
- **click** on `(unknown selector)` (line 171)
  - calls: openChat
- **click** on `(unknown selector)` (line 175)
  - calls: stopPropagation, confirm, qs, auth, stringify, apiJSON, loadInbox, alert
- **click** on `(unknown selector)` (line 426)
  - handlerName: `loadInbox`
- **click** on `(unknown selector)` (line 431)
  - handlerName: `closeChat`
- **click** on `(unknown selector)` (line 432)
  - handlerName: `sendChatReply`
- **mz:admin-auth** on `(unknown selector)` (line 443)
  - calls: initOnce
- **mz:pane:show** on `#ui-wa` (line 447)
  - calls: initOnce

## static/meatze/chat_widget/chat-widget.js

- **click** on `(unknown selector)` (line 31)
  - handlerName: `openChat`
- **click** on `(unknown selector)` (line 32)
  - handlerName: `closeChat`
- **click** on `(unknown selector)` (line 33)
  - handlerName: `closeChat`
- **click** on `(unknown selector)` (line 229)
  - handlerName: `sendMsg`
- **keydown** on `(unknown selector)` (line 34)
  - calls: closeChat
- **keydown** on `(unknown selector)` (line 230)
  - calls: sendMsg
