(()=>{ 'use strict';
  const $ = s => document.querySelector(s);

  // === shared API/auth (совместно с общим gate)
  const API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5';
  const API_A = API_BASE + '/admin';
  const tok = () => sessionStorage.getItem('mz_admin') || '';
  const qs  = (bust=false)=> (tok()?`?adm=${encodeURIComponent(tok())}`:'') + (bust?(`${tok()?'&':'?'}_=${Date.now()}`):'');
  const auth= (isPost=false)=>{const h={}; if(tok()) h['X-MZ-Admin']=tok(); if(isPost) h['Content-Type']='application/json'; return h;};
  async function apiJSON(url, opt={}) {
    const r = await fetch(url, {...opt, cache:'no-store', headers:{...(opt.headers||{}), 'Cache-Control':'no-cache'}});
    const txt = await r.text(); let j=null;
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`); }
    if (!r.ok) throw new Error(j?.message || j?.code || `HTTP ${r.status}`);
    return j;
  }

  // === panel init (lazy)
  let teachersReady = false;
  async function initTeachersOnce(){
    if (teachersReady || !tok()) return;  // ждём общий вход
    teachersReady = true;
    const esc = s => (s??'').toString().replace(/[&<>"]/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[m]));
    const escAttr = s => esc(s).replace(/"/g,'&quot;');
    const nrm = s => (s ?? '').toString().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
	const debounce = (fn, ms=150)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; };

    const list = $('#mzt-body');
    const searchIn = $('#mzt-search');
    const clearBtn = $('#mzt-clear');
    const msg = $('#mzt-msg');
    let allItems = [];

    // ==========================
    // PENDIENTES POR CORREO
    // ==========================
    const PEND_BASE = API_BASE + '/admin/pending';
    const pBody   = $('#mzp-body');
    const pSearch = $('#mzp-search');
    const pRef    = $('#mzp-refresh');
    const pClr    = $('#mzp-clear');

    let pAll = [];

    async function refreshPending(){
      if (!pBody) return;
      pBody.innerHTML = '<tr><td colspan="4">Cargando…</td></tr>';
      try{
        const j = await apiJSON(`${PEND_BASE}${qs(true)}`, { headers: auth() });
        pAll = j.items || [];
        applyPendingFilter();
      }catch(e){
        pBody.innerHTML = `<tr><td colspan="4">${esc(e.message||'Error')}</td></tr>`;
      }
    }

    function pendingRow(it){
      const tr = document.createElement('tr');
      const name = (it.display_name || '').trim() || (it.email || '');
      const dt = it.created_at ? new Date(it.created_at) : null;
      const dtTxt = dt ? dt.toLocaleString() : '';

      tr.innerHTML = `
        <td>${esc(name)}</td>
        <td>${esc(it.email||'')}</td>
        <td>${esc(dtTxt)}</td>
        <td style="white-space:nowrap; display:flex; gap:8px; flex-wrap:wrap">
          <button class="mz-btn" data-approve data-action="pending.approve_teacher">Confirmar docente</button>
<button class="mz-btn danger" data-student data-action="pending.mark_student">Es alumno</button>

        </td>
      `;

      tr.querySelector('[data-approve]').onclick = async ()=>{
        if (!confirm(`¿Confirmar como docente: ${name}?`)) return;
        try{
          await apiJSON(`${PEND_BASE}/${it.id}/approve-teacher${qs()}`, { method:'POST', headers: auth(true) });
          // после апрува логично обновить и pending, и teachers
          await refreshPending();
          await refreshList();
        }catch(e){ alert(e.message||'Error'); }
      };

      tr.querySelector('[data-student]').onclick = async ()=>{
        if (!confirm(`¿Marcar como alumno y quitar de la lista: ${name}?`)) return;
        try{
          await apiJSON(`${PEND_BASE}/${it.id}/mark-student${qs()}`, { method:'POST', headers: auth(true) });
          await refreshPending();
        }catch(e){ alert(e.message||'Error'); }
      };

      return tr;
    }

    function drawPending(items){
      if (!pBody) return;
      pBody.innerHTML = '';
      if (!items.length){
        pBody.innerHTML = '<tr><td colspan="4">No hay solicitudes pendientes.</td></tr>';
        return;
      }
      for (const it of items) pBody.appendChild(pendingRow(it));
    }

    function applyPendingFilter(){
      const q = nrm(pSearch?.value || '');
      if (!q){ drawPending(pAll); return; }
      const filtered = pAll.filter(it=>{
        const hay = [it.display_name, it.email].map(nrm).join(' ');
        return hay.includes(q);
      });
      drawPending(filtered);
    }

    pRef?.addEventListener('click', refreshPending);
    pClr?.addEventListener('click', ()=>{ if(!pSearch) return; pSearch.value=''; applyPendingFilter(); pSearch.focus(); });
    pSearch?.addEventListener('input', debounce(applyPendingFilter, 150));

    // первичная загрузка pending тоже
    refreshPending();


    async function refreshList(){
      list.innerHTML = '<tr><td colspan="4">Cargando…</td></tr>';
      try{
        const j = await apiJSON(`${API_A}/teachers${qs(true)}`, {headers:auth()});
        allItems = j.items || [];
        applyFilter();
      }catch(e){
        list.innerHTML = `<tr><td colspan="4">${esc(e.message||'Error')}</td></tr>`;
      }
    }

function rowView(it){
  const tr = document.createElement('tr');
  const pref = [it.first_name, it.last_name1, it.last_name2].filter(Boolean).join(' ').trim();
  const name = pref || (it.display_name||'').trim() || (it.email||'');

  tr.innerHTML = `
    <td>${esc(name)}</td>
    <td>${esc(it.email||'')}</td>
    <td>${esc(it.bio||'')}</td>
    <td style="white-space:nowrap; text-align:right">
      <div class="mz-dd" data-dd>
        <button class="mz-dd-btn" type="button" aria-haspopup="menu" aria-expanded="false">
          Acciones <span aria-hidden="true">▾</span>
        </button>
        <div class="mz-dd-menu" role="menu">
          <button class="mz-dd-item" type="button" data-edit role="menuitem">✏️ Editar</button>
          <button class="mz-dd-item danger" type="button" data-del role="menuitem">🗑️ Quitar</button>
        </div>
      </div>
    </td>
  `;

  const dd = tr.querySelector('[data-dd]');
  const btn = dd.querySelector('.mz-dd-btn');

  const open = ()=>{
    dd.dataset.open = 'true';
    btn.setAttribute('aria-expanded','true');
  };
  const close = ()=>{
    dd.dataset.open = 'false';
    btn.setAttribute('aria-expanded','false');
  };
  const toggle = ()=>{
    (dd.dataset.open === 'true') ? close() : open();
  };

  btn.addEventListener('click', (e)=>{ e.stopPropagation(); toggle(); });

  tr.querySelector('[data-edit]').onclick = (e)=>{ e.stopPropagation(); close(); tr.replaceWith(rowEdit(it)); };
  tr.querySelector('[data-del]').onclick  = (e)=>{ e.stopPropagation(); close(); doDelete(it.id); };

  // закрытие при клике вне
  document.addEventListener('click', close, { once:true });

  // закрытие по ESC
  dd.addEventListener('keydown', (e)=>{
    if (e.key === 'Escape') close();
  });

  return tr;
}


function rowEdit(it){
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input class="mz-inp" data-first  placeholder="Nombre" value="${escAttr(it.first_name||'')}"></td>
    <td><input class="mz-inp" data-email  placeholder="E-mail *" value="${escAttr(it.email||'')}"></td>
    <td><input class="mz-inp" data-bio    placeholder="Descripción" value="${escAttr(it.bio||'')}"></td>
    <td style="white-space:nowrap; text-align:right">
      <div class="mz-dd" data-dd>
        <button class="mz-dd-btn" type="button" aria-haspopup="menu" aria-expanded="false">
          Guardar <span aria-hidden="true">▾</span>
        </button>
        <div class="mz-dd-menu" role="menu">
          <button class="mz-dd-item" type="button" data-save role="menuitem">💾 Guardar</button>
          <button class="mz-dd-item" type="button" data-cancel role="menuitem">↩️ Cancelar</button>
          <button class="mz-dd-item danger" type="button" data-del role="menuitem">🗑️ Quitar</button>
        </div>
      </div>
    </td>
  `;

  const dd = tr.querySelector('[data-dd]');
  const btn = tr.querySelector('.mz-dd-btn');
  const open = ()=>{ dd.dataset.open='true'; btn.setAttribute('aria-expanded','true'); };
  const close= ()=>{ dd.dataset.open='false'; btn.setAttribute('aria-expanded','false'); };
  const toggle=()=> (dd.dataset.open==='true') ? close() : open();
  btn.addEventListener('click', (e)=>{ e.stopPropagation(); toggle(); });
  document.addEventListener('click', close, { once:true });

  const getBody = ()=>({
    email:      tr.querySelector('[data-email]').value.trim().toLowerCase(),
    first_name: tr.querySelector('[data-first]').value.trim(),
    last_name1: it.last_name1 || '',
    last_name2: it.last_name2 || '',
    bio:        tr.querySelector('[data-bio]').value
  });

  tr.querySelector('[data-cancel]').onclick = (e)=>{ e.stopPropagation(); close(); tr.replaceWith(rowView(it)); };

  tr.querySelector('[data-del]').onclick = (e)=>{ e.stopPropagation(); close(); doDelete(it.id); };

  tr.querySelector('[data-save]').onclick = async (e)=>{
    e.stopPropagation(); close();
    const body = getBody();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)){
      alert('E-mail inválido'); return;
    }
    try{
      await apiJSON(`${API_A}/teachers${qs()}`, {
        method:'POST',
        headers: auth(true),
        body: JSON.stringify(body)
      });
      await refreshList();
    }catch(err){
      alert(err.message || 'Error');
    }
  };

  return tr;
}


    async function doDelete(id){
      if (!confirm('¿Quitar acceso docente?')) return;
      try{
        await apiJSON(`${API_A}/teachers/${id}/delete${qs()}`, {method:'POST', headers:auth(true)});
        refreshList();
      }catch(e){ alert(e.message||'Error'); }
    }

    function drawRows(items){
      list.innerHTML = '';
      if (!items.length){ list.innerHTML = '<tr><td colspan="4">No hay docentes aún.</td></tr>'; return; }
      for (const it of items) list.appendChild(rowView(it));
    }

    function applyFilter(){
      const q = nrm(searchIn?.value || '');
      if (!q) { drawRows(allItems); return; }
      const filtered = allItems.filter(it=>{
        const hay = [it.display_name, it.first_name, it.last_name1, it.last_name2, it.email, it.bio].map(nrm).join(' ');
        return hay.includes(q);
      });
      drawRows(filtered);
    }

    searchIn?.addEventListener('input', debounce(applyFilter, 150));
    clearBtn?.addEventListener('click', ()=>{ if(!searchIn) return; searchIn.value=''; applyFilter(); searchIn.focus(); });

    // Upsert
    $('#mzt-save')?.addEventListener('click', async ()=>{
      msg.textContent='';
      const body = {
        email:      $('#mzt-email').value.trim().toLowerCase(),
        first_name: $('#mzt-first').value.trim(),
        last_name1: $('#mzt-last1').value.trim(),
        last_name2: $('#mzt-last2').value.trim(),
        bio:        $('#mzt-bio').value
      };
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)){
        msg.innerHTML='<span class="mz-help" style="color:#b90e2e">E-mail inválido</span>'; return;
      }
      try{
        await apiJSON(`${API_A}/teachers${qs()}`, {method:'POST', headers:auth(true), body:JSON.stringify(body)});
        $('#mzt-email').value = $('#mzt-first').value = $('#mzt-last1').value = $('#mzt-last2').value = '';
        $('#mzt-bio').value = '';
        msg.innerHTML = '<span class="mz-help" style="color:#0b6d22">Guardado.</span>';
        refreshList();
      }catch(e){
        msg.innerHTML = '<span class="mz-help" style="color:#b90e2e">'+(e.message||'Error')+'</span>';
      }
    });

    // первичная загрузка
    refreshList();
  }

  // 1) init сразу, если токен уже есть (перезагрузка)
  if (tok()) initTeachersOnce();

  // 2) init при общем входе (shared gate)
  document.addEventListener('mz:admin-auth', (e)=>{ if (e?.detail?.ok) initTeachersOnce(); });

  // 3) ленивый init при показе панели «Docentes»
  document.getElementById('ui-teachers')
    ?.addEventListener('mz:pane:show', (ev)=>{ if (ev?.detail?.mod==='teachers') initTeachersOnce(); });
})();
