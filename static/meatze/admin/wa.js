(() => {
  'use strict';

  const $ = (s, root=document) => root.querySelector(s);

  let inboxCache   = [];
  let currentChatWa = null;
  let lastInboxIds  = new Set();
  let newMsgThreads = new Set();
  let autoTimer     = null;

	const notifyAudio = new Audio(
	  window.MZ_NOTIFY_URL || '/static/files/meatze_notify.mp3'
	);

  // В Django wpApiSettings нет, работаем напрямую с /meatze/v5
  const API_BASE = '/meatze/v5';
  const API_N    = API_BASE + '/notify';
  const tok      = () => sessionStorage.getItem('mz_admin') || '';
  const qs       = (bust=false)=> (tok()?`?adm=${encodeURIComponent(tok())}`:'') + (bust?(`${tok()?'&':'?'}_=${Date.now()}`):'');
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

  // ===== уведомления =====
  function showNewMsgToast(from, text){
    if (!('Notification' in window)) return;

    if (Notification.permission === 'granted'){
      new Notification(`Nuevo mensaje de ${from}`, {
        body: text.slice(0,120),
        icon: 'https://meatze.eus/wp-content/uploads/2024/11/meatze-icon.png'
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