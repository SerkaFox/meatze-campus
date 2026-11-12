(() => {
  'use strict';

  const $ = (s, root=document) => root.querySelector(s);

  let inboxCache   = [];
  let currentChatWa = null;
  let lastInboxIds  = new Set();
  let newMsgThreads = new Set();
  let autoTimer     = null;

	const notifyAudio = new Audio(
	  window.MZ_NOTIFY_URL || '/static/files/aurora_notify.mp3'
	);

  // В Django wpApiSettings нет, работаем напрямую с /v5
  const API_BASE = '/v5';
  const API_N    = API_BASE + '/notify';
  const tok      = () => sessionStorage.getItem('mz_admin') || '';
const qs = (bust=false) => (bust ? `?_=${Date.now()}` : '');
  const auth     = (isPost=false)=> {
    const h={};
    if (tok()) h['X-MZ-Admin'] = tok();
    if (isPost) h['Content-Type']='application/json';
    return h;
  };
  async function apiJSON(url, opt={}) {
    const r   = await fetch(url, {...opt, cache:'no-store', headers:{...(opt.headers||{}), 'Cache-Control':'no-cache'}});
    const txt = await r.text();
    let j = null;
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`); }
    if (!r.ok) throw new Error(j?.message || j?.code || `HTTP ${r.status}`);
    return j;
  }

  const audienceLabels = {
    students: 'Alumnos',
    teachers: 'Docentes',
    guests: 'Invitados',
  };

  const templates = {
    students: [
      {
        id:'no-class',
        title:'No hay clase',
        hint:'Cancelación puntual',
        text:'Hola, {nombre}.\n\nTe informamos de que el día {fecha} no habrá clase del curso {curso}.\n\nEl centro confirmará la recuperación o el ajuste del calendario por este mismo canal.\n\nUn saludo,\nУчебный центр'
      },
      {
        id:'reschedule',
        title:'Cambio de horario',
        hint:'Clase movida',
        text:'Hola, {nombre}.\n\nLa sesión del curso {curso} prevista para {fecha} se traslada a {detalle}.\n\nPor favor, revisa el calendario actualizado en el campus.\n\nUn saludo,\nУчебный центр'
      },
      {
        id:'practice',
        title:'Prácticas',
        hint:'Inicio o reunión',
        text:'Hola, {nombre}.\n\nTe recordamos que la fase de prácticas de {curso} está prevista para {fecha}. Detalle: {detalle}.\n\nSi tienes alguna duda, responde a este mensaje.\n\nУчебный центр'
      },
      {
        id:'start',
        title:'Inicio de curso',
        hint:'Bienvenida',
        text:'Hola, {nombre}.\n\nEl curso {curso} comienza el día {fecha}. Detalle: {detalle}.\n\nTe esperamos. Recibirás cualquier cambio por este canal.\n\nУчебный центр'
      },
    ],
    teachers: [
      {
        id:'calendar',
        title:'Calendario',
        hint:'Aviso docente',
        text:'Hola, {nombre}.\n\nSe ha actualizado el calendario del curso {curso}. Fecha clave: {fecha}. Detalle: {detalle}.\n\nPor favor, revisa horarios, festivos y sesiones asignadas.\n\nУчебный центр'
      },
      {
        id:'assigned',
        title:'Curso asignado',
        hint:'Nueva asignación',
        text:'Hola, {nombre}.\n\nTe hemos asignado el curso {curso}. Inicio previsto: {fecha}. Detalle: {detalle}.\n\nYa puedes revisar el panel docente y el calendario.\n\nУчебный центр'
      },
      {
        id:'schedule-change',
        title:'Cambio de agenda',
        hint:'Ajuste horario',
        text:'Hola, {nombre}.\n\nHay un ajuste en el horario del curso {curso} para {fecha}. Detalle: {detalle}.\n\nConfirma recibido cuando puedas.\n\nУчебный центр'
      },
    ],
    guests: [
      {
        id:'invite',
        title:'Invitación',
        hint:'Contacto externo',
        text:'Hola, {nombre}.\n\nDesde Учебный центр queremos invitarte a {detalle} el día {fecha}.\n\nSerá un placer contar contigo.\n\nUn saludo.'
      },
      {
        id:'holiday',
        title:'Felicitación',
        hint:'Fiestas',
        text:'Hola, {nombre}.\n\nDesde Учебный центр te deseamos unas felices fiestas. Gracias por seguir cerca de nuestra comunidad formativa.\n\nUn saludo cordial.'
      },
      {
        id:'postcard',
        title:'Postal',
        hint:'Mensaje con imagen',
        text:'Hola, {nombre}.\n\nTe enviamos una felicitación especial de parte de Учебный центр.\n\nEsperamos que tengas un excelente día.'
      },
    ],
  };

  const defaultAutomations = [
    {
      id:'student_no_class',
      enabled:false,
      audience:'students',
      event:'Día sin clase marcado en calendario',
      timing:'Enviar 24 horas antes y repetir 2 horas antes',
      title:'Avisar a alumnos: no hay clase',
      mode:'auto',
      message:templates.students[0].text,
    },
    {
      id:'student_reschedule',
      enabled:false,
      audience:'students',
      event:'Cambio de hora o aula en Horarios',
      timing:'Enviar al guardar el cambio',
      title:'Avisar a alumnos: cambio de horario',
      mode:'auto',
      message:templates.students[1].text,
    },
    {
      id:'student_practice',
      enabled:false,
      audience:'students',
      event:'Fecha de prácticas configurada',
      timing:'Enviar 7 días antes y 1 día antes',
      title:'Recordatorio de prácticas',
      mode:'auto',
      message:templates.students[2].text,
    },
    {
      id:'teacher_assigned',
      enabled:false,
      audience:'teachers',
      event:'Docente asignado a curso',
      timing:'Enviar al asignar docente',
      title:'Avisar a docente: curso asignado',
      mode:'auto',
      message:templates.teachers[1].text,
    },
    {
      id:'teacher_calendar',
      enabled:false,
      audience:'teachers',
      event:'Calendario del curso actualizado',
      timing:'Enviar resumen al guardar horario',
      title:'Avisar a docentes: calendario',
      mode:'draft',
      message:templates.teachers[0].text,
    },
    {
      id:'guest_holiday',
      enabled:false,
      audience:'guests',
      event:'Campaña manual de fiestas',
      timing:'Preparar como campaña manual',
      title:'Invitados: felicitación',
      mode:'draft',
      message:templates.guests[1].text,
    },
  ];

  let crmAudience = 'students';
  let crmTemplate = templates.students[0];
  let automations = defaultAutomations.map(x => ({...x}));

  function todayISO(){
    return new Date().toISOString().slice(0, 10);
  }

  function fillVars(text){
    const course = ($('#mzw-course')?.value || 'IFCT0209').trim();
    const date = ($('#mzw-date')?.value || todayISO()).trim();
    const detail = ($('#mzw-extra')?.value || 'pendiente de confirmar').trim();
    return String(text || '')
      .replaceAll('{nombre}', 'María')
      .replaceAll('{curso}', course)
      .replaceAll('{fecha}', date)
      .replaceAll('{detalle}', detail);
  }

  function renderCrmTemplates(){
    const list = $('#mzw-template-list');
    if (!list) return;
    list.innerHTML = '';
    (templates[crmAudience] || []).forEach(t => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = t.id === crmTemplate.id ? 'is-active' : '';
      btn.innerHTML = `${escapeHtml(t.title)}<span>${escapeHtml(t.hint)}</span>`;
      btn.addEventListener('click', () => {
        crmTemplate = t;
        const msg = $('#mzw-message');
        if (msg) msg.value = t.text;
        renderCrmTemplates();
        updateCrmPreview();
      });
      list.appendChild(btn);
    });
    const chip = $('#mzw-template-chip');
    if (chip) chip.textContent = crmTemplate.title || 'Plantilla';
  }

  function setAudience(audience){
    crmAudience = audience;
    crmTemplate = (templates[crmAudience] || templates.students)[0];
    document.querySelectorAll('[data-wa-audience]').forEach(btn => {
      btn.classList.toggle('is-active', btn.dataset.waAudience === crmAudience);
    });
    const chip = $('#mzw-audience-chip');
    if (chip) chip.textContent = audienceLabels[crmAudience] || 'Audiencia';
    const msg = $('#mzw-message');
    if (msg) msg.value = crmTemplate.text;
    renderCrmTemplates();
    renderRecipientHints();
    updateCrmPreview();
  }

  function renderRecipientHints(){
    const box = $('#mzw-recipient-hints');
    if (!box) return;
    const hints = {
      students: [
        ['Segmentos', 'Por curso, grupo, sede o alumnos seleccionados'],
        ['Casos', 'No clase, cambio de horario, inicio, prácticas, recordatorios'],
      ],
      teachers: [
        ['Segmentos', 'Por curso asignado, sede o equipo docente'],
        ['Casos', 'Calendario, cambios, asignación de curso, coordinación'],
      ],
      guests: [
        ['Segmentos', 'Contactos externos, empresas, invitados y antiguos alumnos'],
        ['Casos', 'Invitaciones, felicitaciones, postales y campañas'],
      ],
    }[crmAudience] || [];
    box.innerHTML = hints.map(x => `<div class="wa-mini-item"><b>${escapeHtml(x[0])}</b>${escapeHtml(x[1])}</div>`).join('');
  }

  function updateCrmPreview(){
    const msg = $('#mzw-message');
    const txt = msg ? msg.value : '';
    const preview = $('#mzw-preview-text');
    if (preview) preview.textContent = fillVars(txt || crmTemplate.text);
    const title = $('#mzw-plan-title');
    const sub = $('#mzw-plan-sub');
    if (title) title.textContent = `${audienceLabels[crmAudience]} · ${crmTemplate.title}`;
    if (sub) sub.textContent = 'Revisa variables, tono y fecha antes de activar o enviar.';
  }

  function renderExamples(){
    const grid = $('#mzw-examples-grid');
    if (!grid) return;
    const all = Object.entries(templates).flatMap(([aud, arr]) => arr.map(t => ({...t, audience:aud})));
    grid.innerHTML = '';
    all.forEach(t => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'wa-example-card';
      btn.innerHTML = `<b>${escapeHtml(audienceLabels[t.audience])} · ${escapeHtml(t.title)}</b><span>${escapeHtml(t.text).slice(0, 120)}...</span>`;
      btn.addEventListener('click', () => {
        setAudience(t.audience);
        crmTemplate = t;
        const msg = $('#mzw-message');
        if (msg) msg.value = t.text;
        renderCrmTemplates();
        updateCrmPreview();
        document.getElementById('mzw-crm')?.scrollIntoView({behavior:'smooth', block:'start'});
      });
      grid.appendChild(btn);
    });
  }

  function renderAutomations(){
    const grid = $('#mzw-auto-grid');
    if (!grid) return;
    grid.innerHTML = '';
    automations.forEach(rule => {
      const card = document.createElement('div');
      card.className = 'wa-auto-rule' + (rule.enabled ? ' is-on' : '');
      card.innerHTML = `
        <div class="wa-auto-rule-head">
          <div>
            <h4>${escapeHtml(rule.title)}</h4>
            <p>${escapeHtml(audienceLabels[rule.audience] || rule.audience)}</p>
          </div>
          <label class="wa-switch" title="Activar automatización">
            <input type="checkbox" data-auto-toggle="${escapeHtml(rule.id)}" ${rule.enabled ? 'checked' : ''}>
            <span></span>
          </label>
        </div>
        <div class="wa-auto-meta">
          <div><span>Evento</span><b>${escapeHtml(rule.event)}</b></div>
          <div><span>Cuándo</span><b>${escapeHtml(rule.timing)}</b></div>
          <div><span>Modo</span><b>${rule.mode === 'auto' ? 'Automático' : 'Borrador revisable'}</b></div>
        </div>
        <div class="wa-auto-actions">
          <button type="button" class="mz-btn link sm" data-auto-load="${escapeHtml(rule.id)}">Editar texto</button>
          <button type="button" class="mz-btn link sm" data-auto-mode="${escapeHtml(rule.id)}">${rule.mode === 'auto' ? 'Pasar a borrador' : 'Pasar a auto'}</button>
        </div>
      `;
      grid.appendChild(card);
    });
    const n = automations.filter(x => x.enabled).length;
    const enabled = $('#mzw-auto-enabled');
    if (enabled) enabled.textContent = `${n} activa${n === 1 ? '' : 's'}`;
  }

  async function loadAutomations(){
    try{
      const j = await apiJSON(`${API_N}/wa-automations${qs(true)}`, {headers:auth()});
      const saved = j?.value?.automations;
      if (Array.isArray(saved) && saved.length){
        const byId = new Map(defaultAutomations.map(x => [x.id, x]));
        automations = saved.map(x => ({...(byId.get(x.id) || {}), ...x}));
      }
    }catch(e){
      console.warn('wa automations load failed', e);
    }
    renderAutomations();
  }

  async function saveAutomations(){
    const statusEl = $('#mzw-auto-status');
    if (statusEl) statusEl.textContent = 'Guardando reglas...';
    try{
      await apiJSON(`${API_N}/wa-automations${qs()}`, {
        method:'POST',
        headers:auth(true),
        body:JSON.stringify({automations})
      });
      if (statusEl) statusEl.textContent = 'Reglas guardadas.';
    }catch(e){
      if (statusEl) statusEl.textContent = e.message || 'Error guardando reglas.';
    }
  }

  function bindCrm(){
    document.querySelectorAll('[data-wa-audience]').forEach(btn => {
      btn.addEventListener('click', () => setAudience(btn.dataset.waAudience || 'students'));
    });
    ['#mzw-course', '#mzw-date', '#mzw-extra', '#mzw-message'].forEach(sel => {
      $(sel)?.addEventListener('input', updateCrmPreview);
    });
    $('#mzw-copy')?.addEventListener('click', async () => {
      const text = fillVars($('#mzw-message')?.value || '');
      try{
        await navigator.clipboard.writeText(text);
        const s = $('#mzw-status');
        if (s) s.textContent = 'Texto copiado.';
      }catch(_){}
    });
    $('#mzw-save')?.addEventListener('click', () => {
      localStorage.setItem('mzw_crm_draft', JSON.stringify({
        audience:crmAudience,
        message:$('#mzw-message')?.value || '',
        course:$('#mzw-course')?.value || '',
        date:$('#mzw-date')?.value || '',
        extra:$('#mzw-extra')?.value || '',
      }));
      const s = $('#mzw-status');
      if (s) s.textContent = 'Borrador guardado en este navegador.';
    });
    $('#mzw-clear')?.addEventListener('click', () => {
      const msg = $('#mzw-message');
      if (msg) msg.value = '';
      updateCrmPreview();
    });
    $('#mzw-mark-ready')?.addEventListener('click', () => {
      const s = $('#mzw-status');
      if (s) s.textContent = 'Mensaje marcado como listo. La automatización real requiere el conector WhatsApp Web por QR.';
    });
    $('#mzw-auto-save')?.addEventListener('click', saveAutomations);
    document.addEventListener('change', e => {
      const t = e.target.closest('[data-auto-toggle]');
      if (!t) return;
      const rule = automations.find(x => x.id === t.dataset.autoToggle);
      if (rule) rule.enabled = !!t.checked;
      renderAutomations();
    });
    document.addEventListener('click', e => {
      const load = e.target.closest('[data-auto-load]');
      if (load){
        const rule = automations.find(x => x.id === load.dataset.autoLoad);
        if (!rule) return;
        setAudience(rule.audience || 'students');
        const msg = $('#mzw-message');
        if (msg) msg.value = rule.message || '';
        updateCrmPreview();
        document.getElementById('mzw-crm')?.scrollIntoView({behavior:'smooth', block:'start'});
      }
      const mode = e.target.closest('[data-auto-mode]');
      if (mode){
        const rule = automations.find(x => x.id === mode.dataset.autoMode);
        if (!rule) return;
        rule.mode = rule.mode === 'auto' ? 'draft' : 'auto';
        renderAutomations();
      }
    });
    const dateEl = $('#mzw-date');
    if (dateEl && !dateEl.value) dateEl.value = todayISO();
    try{
      const draft = JSON.parse(localStorage.getItem('mzw_crm_draft') || '{}');
      if (draft && draft.message){
        if ($('#mzw-course')) $('#mzw-course').value = draft.course || $('#mzw-course').value;
        if ($('#mzw-date')) $('#mzw-date').value = draft.date || $('#mzw-date').value;
        if ($('#mzw-extra')) $('#mzw-extra').value = draft.extra || '';
        setAudience(draft.audience || 'students');
        if ($('#mzw-message')) $('#mzw-message').value = draft.message;
      }else{
        setAudience('students');
      }
    }catch(_){
      setAudience('students');
    }
    renderExamples();
  }

  // ===== уведомления =====
  function showNewMsgToast(from, text){
    if (!('Notification' in window)) return;

    if (Notification.permission === 'granted'){
      new Notification(`Nuevo mensaje de ${from}`, {
        body: text.slice(0,120),
        icon: '/static/favicon.png'
      });
    }
    else if (Notification.permission !== 'denied'){
      Notification.requestPermission();
    }
  }

  // ===== helper: localidad из строки inbox =====
  function getRowLoc(row){
    if (!row) return '';
    const loc = row.sub_loc || row.loc || '';
    return (loc || '').toString().trim();
  }

  // ===== загрузка inbox =====
  async function loadInbox(){
    const listEl = $('#mzi-thread-list');
    if (!listEl) return;

    listEl.innerHTML = '<div style="padding:8px" class="mz-help">Cargando…</div>';

    try{
      const base = `${API_N}/wa-inbox${qs(true)}`;
      const url  = base + `&limit=50`;

      const j     = await apiJSON(url, { headers: auth() });
      const items = j.items || [];

      const prevIds   = new Set(lastInboxIds);
      const newIds    = new Set(items.map(r => r.id));
      const newlyFrom = new Set();

      for (const row of items){
        if (!prevIds.has(row.id)){
          const waPlain = String(row.wa || '').replace(/\D+/g,'');
          if (waPlain) newlyFrom.add(waPlain);
        }
      }

      lastInboxIds = newIds;
      newlyFrom.forEach(wa => newMsgThreads.add(wa));

      inboxCache = items;
      renderInboxThreadList();

    }catch(e){
      console.error(e);
      listEl.innerHTML = '<div style="padding:8px" class="mz-help">Error cargando mensajes</div>';
    }
  }

  // авто-обновление только для чата
  async function autoRefreshInbox(){
    try{
      const url = `${API_N}/wa-inbox${qs(true)}&limit=50`;
      const j   = await apiJSON(url, {headers:auth()});
      const items = j.items || [];
      const newIds = new Set(items.map(r => r.id));

      const newMsgs = items.filter(r => !lastInboxIds.has(r.id));

      if (newMsgs.length){
        try { notifyAudio.play(); } catch(_){}

        const r = newMsgs[0];
        const fromName = r.sub_name || r.wa_name || r.wa;
        showNewMsgToast(fromName, r.msg || '');

        inboxCache = items;
        renderInboxThreadList();
      }

      lastInboxIds = newIds;
    }catch(e){
      console.warn('auto-refresh inbox failed', e);
    }
  }

  // ===== список бесед =====
function buildThreadItem(t, activeShort){
  const hasNew   = newMsgThreads.has(t.wa);
  const isActive = activeShort && t.wa === activeShort;

  const name      = (t.name || 'Contacto').trim() || 'Contacto';
  const numLabel  = t.wa.length === 9 ? `+34${t.wa}` : `+${t.wa}`;
  const last      = (t.lastMsg || '').replace(/\s+/g,' ').trim().slice(0, 70) || '—';
  const dateShort = t.lastDate ? String(t.lastDate).replace('T',' ').slice(0,16) : '';
  const loc       = t.loc ? ` · ${t.loc}` : '';

  const row = document.createElement('div');
  row.className = 'wa-thread' + (isActive ? ' is-active' : '') + (hasNew && !isActive ? ' is-new' : '');
  row.setAttribute('data-thread-wa', t.wa);
  row.setAttribute('data-action', 'wa.thread.open');

  row.innerHTML = `
    <div class="wa-thread-main">
      <div class="wa-thread-top">
        <div class="wa-thread-name">${escapeHtml(name)}</div>
        ${hasNew && !isActive ? `<span class="wa-pill new">Nuevo</span>` : ``}
      </div>

      <div class="wa-thread-meta">${escapeHtml(numLabel + loc)}</div>
      <div class="wa-thread-last">${escapeHtml(last)}</div>

      <div class="wa-thread-foot">
        <span class="wa-time">${escapeHtml(dateShort)}</span>
      </div>
    </div>

    <button type="button" class="wa-del" title="Eliminar" data-del-thread>🗑</button>
  `;

  // открыть чат кликом по карточке (кроме удаления)
  row.addEventListener('click', ()=>openChat(t.wa, name));

  const delBtn = row.querySelector('[data-del-thread]');
  if (delBtn){
    delBtn.addEventListener('click', async (ev)=> {
      ev.stopPropagation();
      if (!confirm('¿Eliminar esta conversación de la bandeja?')) return;
      try{
        await apiJSON(`${API_N}/wa-inbox-delete${qs()}`, {
          method:'POST',
          headers:auth(true),
          body:JSON.stringify({ wa: t.wa })
        });
        loadInbox();
      }catch(e){
        alert(e.message || 'Error al eliminar conversación');
      }
    });
  }

  return row;
}

// безопасный escape для innerHTML
function escapeHtml(s){
  return String(s ?? '').replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[m]));
}


  function renderInboxThreadList(){
    const listEl = $('#mzi-thread-list');
    if (!listEl) return;

    const srcSel    = $('#mzi-src');
    const locFilter = srcSel ? (srcSel.value || '') : '';

    let items = inboxCache || [];

    if (locFilter) {
      items = items.filter(row => getRowLoc(row) === locFilter);
    }

    const threadsMap = new Map();
    for (const row of items) {
      const wa = String(row.wa || '').replace(/\D+/g,'');
      if (!wa) continue;

      const key  = wa;
      const name = (row.sub_name || row.wa_name || row.name || '').trim();
      const loc  = getRowLoc(row);
      const msg  = row.msg || '';
      const dt   = row.created_at || '';

      if (!threadsMap.has(key)) {
        threadsMap.set(key, {
          wa: key,
          name: name || 'Contacto',
          loc,
          lastMsg: msg,
          lastDate: dt,
          msgsCount: 1,
        });
      } else {
        const t = threadsMap.get(key);
        t.msgsCount++;
        if (!t.lastDate || (new Date(dt) > new Date(t.lastDate))) {
          t.lastMsg  = msg;
          t.lastDate = dt;
        }
      }
    }

    const threads = Array.from(threadsMap.values());

    if (!threads.length){
      listEl.innerHTML = '<div style="padding:8px" class="mz-help">Sin mensajes</div>';
      return;
    }

    threads.sort((a,b) => new Date(b.lastDate || 0) - new Date(a.lastDate || 0));

    listEl.innerHTML = '';
    const activeShort = currentChatWa ? String(currentChatWa).replace(/\D+/g,'') : null;

    for (const t of threads) {
      const item = buildThreadItem(t, activeShort);
      listEl.appendChild(item);
    }

    if (currentChatWa) {
      renderChatLog(currentChatWa);
    }
    highlightActiveThread(currentChatWa);
  }

function highlightActiveThread(wa){
  const waStr = wa ? String(wa).replace(/\D+/g,'') : null;
  document.querySelectorAll('#mzi-thread-list [data-thread-wa]').forEach(el => {
    const isActive = waStr && el.getAttribute('data-thread-wa') === waStr;
    el.classList.toggle('is-active', !!isActive);
  });
}


  // ===== чат =====
  function openChat(wa, name){
    currentChatWa = String(wa || '');
    const shortWa = currentChatWa.replace(/\D+/g,'');

    if (shortWa) newMsgThreads.delete(shortWa);

    const box   = $('#mzi-chat');
    const title = $('#mzi-chat-title');
    const msgEl = $('#mzi-chat-msg');
    const input = $('#mzi-chat-input');
    const empty = $('#mzi-chat-empty');

    if (!box || !title) return;

    title.textContent = `${name || 'Contacto'} · ${shortWa || currentChatWa}`;
    if (msgEl) {
      msgEl.textContent = '';
      msgEl.style.color = '#6b7280';
    }
    if (input) {
      input.value = '';
      input.focus();
    }
    if (empty) empty.style.display = 'none';
    box.style.display = 'block';

    renderChatLog(currentChatWa);
    highlightActiveThread(currentChatWa);
  }

  function closeChat(){
    const box   = $('#mzi-chat');
    const empty = $('#mzi-chat-empty');
    if (box)   box.style.display   = 'none';
    if (empty) empty.style.display = 'block';
    currentChatWa = null;
    highlightActiveThread(null);
  }

  function renderChatLog(wa){
    const log = $('#mzi-chat-log');
    if (!log) return;

    const waStr = String(wa || '');
    const msgs  = (inboxCache || []).filter(r => String(r.wa || '').replace(/\D+/g,'') === waStr);

    if (!msgs.length){
      log.innerHTML = '<div class="mz-help">Sin historial todavía.</div>';
      return;
    }

    msgs.sort((a,b) => {
      const da = new Date(a.created_at || '');
      const db = new Date(b.created_at || '');
      return da - db;
    });

    log.innerHTML = '';

    msgs.forEach(row => {
      const div = document.createElement('div');
      div.style.marginBottom = '6px';

      const isOut = row.direction === 'out';

      const wrap = document.createElement('div');
      wrap.style.display       = 'flex';
      wrap.style.justifyContent = isOut ? 'flex-end' : 'flex-start';

      const bubble = document.createElement('div');
      bubble.style.display    = 'inline-block';
      bubble.style.padding    = '6px 8px';
      bubble.style.borderRadius = '10px';
      bubble.style.maxWidth   = '75%';
      bubble.style.whiteSpace = 'pre-wrap';
      bubble.style.background = isOut ? '#d1fae5' : '#e5f3ff';

      const ts   = row.created_at || '';
      const meta = document.createElement('div');
      meta.className        = 'mz-help';
      meta.style.marginBottom = '2px';
      meta.textContent      = ts;

      const body = document.createElement('div');
      body.textContent = row.msg || '';

      bubble.appendChild(meta);
      bubble.appendChild(body);
      wrap.appendChild(bubble);
      div.appendChild(wrap);
      log.appendChild(div);
    });

    log.scrollTop = log.scrollHeight;
  }

  async function sendChatReply(){
    const wa    = currentChatWa;
    const input = $('#mzi-chat-input');
    const msgEl = $('#mzi-chat-msg');

    if (!wa || !input || !msgEl) return;

    const text = (input.value || '').trim();
    if (!text){
      msgEl.textContent = 'Escribe un mensaje.';
      msgEl.style.color = '#b90e2e';
      return;
    }

    msgEl.textContent = 'Enviando…';
    msgEl.style.color = '#6b7280';

    try{
      await apiJSON(`${API_N}/wa-reply${qs()}`, {
        method:'POST',
        headers:auth(true),
        body:JSON.stringify({ wa, text })
      });

      msgEl.textContent = 'Enviado ✔';
      msgEl.style.color = '#0b6d22';
      input.value       = '';

      inboxCache.push({
        wa: String(wa),
        msg: text,
        created_at: new Date().toISOString().slice(0,19).replace('T',' '),
        wa_name: '',
        sub_name: '',
        direction: 'out'
      });
      renderChatLog(wa);

    }catch(e){
      console.error(e);
      msgEl.textContent = e.message || 'Error al enviar';
      msgEl.style.color = '#b90e2e';
    }
  }

  // ===== init только для чата (ui-wa) =====
  let inited = false;
  function initOnce(){
    if (inited || !tok()) return;
    inited = true;
    boot();
  }

  function boot(){
    const srcSel   = $('#mzi-src');
    const btnInbox = $('#mzi-refresh');
    if (srcSel) {
      srcSel.addEventListener('change', renderInboxThreadList);
    }
    if (btnInbox) {
      btnInbox.addEventListener('click', loadInbox);
    }

    const chatClose = $('#mzi-chat-close');
    const chatSend  = $('#mzi-chat-send');
    if (chatClose) chatClose.addEventListener('click', closeChat);
    if (chatSend)  chatSend.addEventListener('click', sendChatReply);

    bindCrm();
    loadAutomations();
    loadInbox();

    if (!autoTimer) {
      autoTimer = setInterval(autoRefreshInbox, 10000);
    }
  }

  if (tok()) initOnce();

  document.addEventListener('mz:admin-auth', (e)=> {
    if (e?.detail?.ok) initOnce();
  });

  document.getElementById('ui-wa')
    ?.addEventListener('mz:pane:show', (ev)=> {
      const mod = ev?.detail?.mod;
      if (mod === 'wa') initOnce();
    });

})();
