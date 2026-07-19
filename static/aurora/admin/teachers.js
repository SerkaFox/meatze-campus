(()=>{ 'use strict';
  const $ = s => document.querySelector(s);

  // === shared API/auth (совместно с общим gate)
  const API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/v5';
  const API_A = API_BASE + '/admin';
  const tok = () => sessionStorage.getItem('mz_admin') || '';
  const qs = (bust=false) => (bust ? `?_=${Date.now()}` : '');
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
  let refreshTeachersList = null;  
  async function initTeachersOnce(){
// ===== Dropdown manager (one-open-at-a-time) =====
let openDD = null;

function closeDD(dd){
  if (!dd) return;
  dd.dataset.open = 'false';
  const btn = dd.querySelector('.mz-dd-btn');
  if (btn) btn.setAttribute('aria-expanded', 'false');
  if (openDD === dd) openDD = null;
}

function openDDOnly(dd){
  if (!dd) return;
  if (openDD && openDD !== dd) closeDD(openDD);
  dd.dataset.open = 'true';
  const btn = dd.querySelector('.mz-dd-btn');
  if (btn) btn.setAttribute('aria-expanded', 'true');
  openDD = dd;
}

// глобальное закрытие по клику вне
document.addEventListener('click', (e)=>{
  if (!openDD) return;
  if (openDD.contains(e.target)) return;
  closeDD(openDD);
});

// закрытие по ESC
document.addEventListener('keydown', (e)=>{
  if (e.key !== 'Escape') return;
  if (!openDD) return;
  closeDD(openDD);
});

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
	const cursosText = (it) => {
	  const arr = Array.isArray(it?.cursos) ? it.cursos : [];
	  if (!arr.length) return '—';
	  // компактно: "IFCT0309, TEST2000"
	  return arr.map(x => x?.codigo).filter(Boolean).join(', ') || '—';
	};

	const cursosTitle = (it) => {
	  const arr = Array.isArray(it?.cursos) ? it.cursos : [];
	  if (!arr.length) return '';
	  // tooltip: "IFCT0309 — Título"
	  return arr
		.map(x => `${x.codigo}${x.titulo ? ' — ' + x.titulo : ''}`)
		.join('\n');
	};
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
      list.innerHTML = '<tr><td colspan="5">Cargando…</td></tr>';
      try{
        const j = await apiJSON(`${API_A}/teachers${qs(true)}`, {headers:auth()});
        allItems = j.items || [];
        applyFilter();
      }catch(e){
        list.innerHTML = `<tr><td colspan="5">${esc(e.message||'Error')}</td></tr>`;
      }
    }
  refreshTeachersList = refreshList; 
function rowView(it){
  const tr = document.createElement('tr');

  const full = [
    it.first_name,
    it.last_name1,
    it.last_name2
  ].filter(Boolean);

  const nameBlock = full.length
    ? `
      <div class="t-name">
        ${full.map(x => `<div>${esc(x)}</div>`).join('')}
      </div>
    `
    : esc(it.email||'');

  const cTxt = cursosText(it);
  const cTip = cursosTitle(it);

  tr.innerHTML = `
    <td>${nameBlock}</td>
    <td>${esc(it.email||'')}</td>
    <td>${esc(it.wa || '')}</td>
    <td title="${escAttr(cTip)}">${esc(cTxt)}</td>
    <td style="white-space:nowrap; text-align:right">
      <div class="t-actions">
        <button class="t-ico" type="button" data-edit>✏️</button>
        <button class="t-ico danger" type="button" data-del>🗑️</button>
      </div>
    </td>
  `;

  tr.querySelector('[data-edit]').onclick = ()=> tr.replaceWith(rowEdit(it));
  tr.querySelector('[data-del]').onclick  = ()=> doDelete(it.id);

  return tr;
}



function rowEdit(it){
  const tr = document.createElement('tr');
  tr.dataset.editing = '1';

  const cTxt = cursosText(it);
  const cTip = cursosTitle(it);

  tr.innerHTML = `
    <td>
      <div class="t-name-edit">
        <input class="mz-inp" data-first placeholder="Nombre"
               value="${escAttr(it.first_name||'')}">

        <input class="mz-inp" data-last1 placeholder="1º apellido"
               value="${escAttr(it.last_name1||'')}">

        <input class="mz-inp" data-last2 placeholder="2º apellido"
               value="${escAttr(it.last_name2||'')}">
      </div>
    </td>

    <td>
      <input class="mz-inp"
             value="${escAttr(it.email||'')}"
             disabled
             style="opacity:.6; cursor:not-allowed">
    </td>

    <td>
      <input class="mz-inp" data-wa placeholder="600123123"
             value="${escAttr(it.wa||'')}">
    </td>

    <td title="${escAttr(cTip)}">
      ${esc(cTxt)}
    </td>

    <td style="white-space:nowrap; text-align:right">
      <div class="t-actions">
        <button class="t-ico ok" type="button" data-save>💾</button>
        <button class="t-ico" type="button" data-cancel>✖️</button>
        <button class="t-ico danger" type="button" data-del>🗑️</button>
      </div>
    </td>
  `;

  tr.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter'){ e.preventDefault(); tr.querySelector('[data-save]')?.click(); }
    if (e.key === 'Escape'){ e.preventDefault(); tr.querySelector('[data-cancel]')?.click(); }
  });

  const getBody = ()=>({
    id: it.id,
    // ✅ ВАЖНО: email не берём из input (он disabled) — шлём исходный
    email: (it.email || '').trim().toLowerCase(),
    wa: tr.querySelector('[data-wa]').value.trim(),
    first_name: tr.querySelector('[data-first]').value.trim(),
    last_name1: tr.querySelector('[data-last1]').value.trim(),
    last_name2: tr.querySelector('[data-last2]').value.trim(),
  });

  tr.querySelector('[data-cancel]').onclick = ()=> tr.replaceWith(rowView(it));
  tr.querySelector('[data-del]').onclick    = ()=> doDelete(it.id);

  tr.querySelector('[data-save]').onclick = async ()=>{
    const body = getBody();

    if (!body.email){
      alert('E-mail inválido'); return;
    }

    if (body.wa && !/^\d{9}$/.test(body.wa)){
      alert('WhatsApp debe tener 9 dígitos'); return;
    }

    try{
      await apiJSON(`${API_A}/teachers${qs()}`, {
        method:'POST',
        headers: auth(true),
        body: JSON.stringify(body)
      });
      await refreshList();
    }catch(err){
      const m = String(err?.message || '');
      if (m.includes('email_change_forbidden')){
        alert(
          'No se puede cambiar el e-mail de un docente existente.\n\n' +
          'Solución: elimínalo de la lista y vuelve a añadirlo con el nuevo e-mail.'
        );
        return;
      }
      alert(m || 'Error');
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
      if (!items.length){ list.innerHTML = '<tr><td colspan="5">No hay docentes aún.</td></tr>'; return; }
      for (const it of items) list.appendChild(rowView(it));
    }

    function applyFilter(){
      const q = nrm(searchIn?.value || '');
      if (!q) { drawRows(allItems); return; }
      const filtered = allItems.filter(it=>{
        const hay = [
  it.display_name, it.first_name, it.last_name1, it.last_name2, it.email, it.wa,
  cursosText(it)
].map(nrm).join(' ');
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
		  wa:         $('#mzt-wa').value.trim()
      };
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)){
        msg.innerHTML='<span class="mz-help" style="color:#b90e2e">E-mail inválido</span>'; return;
      }
      try{
        await apiJSON(`${API_A}/teachers${qs()}`, {method:'POST', headers:auth(true), body:JSON.stringify(body)});
		$('#mzt-email').value = '';
		$('#mzt-wa').value = '';
		$('#mzt-first').value = '';
		$('#mzt-last1').value = '';
		$('#mzt-last2').value = '';

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
  ?.addEventListener('mz:pane:show', (ev)=>{
    if (ev?.detail?.mod !== 'teachers') return;
    if (!tok()) return;

    // если панель уже инициализировалась — просто обновим данные
    if (teachersReady && typeof refreshTeachersList === 'function'){
      refreshTeachersList();
      return;
    }

    // иначе — первая инициализация
    initTeachersOnce();
  });
  
  document.addEventListener('mz:teachers-updated', ()=>{
  if (teachersReady && refreshTeachersList) refreshTeachersList();
});
})();
