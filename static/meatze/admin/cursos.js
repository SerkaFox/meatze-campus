(()=>{ 'use strict';
  // === shared auth helpers ===
  const $ = s => document.querySelector(s);
  const API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5';
  const API_A = API_BASE + '/admin';
  const tok = () => sessionStorage.getItem('mz_admin') || '';
const qs = (bust=false) => (bust ? `?_=${Date.now()}` : '');

  const auth= (isPost=false)=>{const h={}; if(tok()) h['X-MZ-Admin']=tok(); if(isPost) h['Content-Type']='application/json'; return h;};
  async function apiJSON(url, opt={}) {
    const r = await fetch(url, {...opt, cache:'no-store', headers:{...(opt.headers||{}), 'Cache-Control':'no-cache'}});
    const txt = await r.text(); let j=null;
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`); }
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`); }
    if (!r.ok) throw new Error(j?.message || j?.code || `HTTP ${r.status}`);
    return j;
  }

  // === panel boot (lazy) ===
let cursosReady = false;
let editingId = null;
let cloneFromCodigo = null;   // ✅ NEW

  async function initCursosOnce(){
  
	  function toModulesArray(modsRaw){
	  if (!modsRaw) return [];
	  // 1) уже массив
	  if (Array.isArray(modsRaw)) return modsRaw;

	  // 2) строка JSON
	  if (typeof modsRaw === 'string') {
		const s = modsRaw.trim();
		if (!s) return [];
		try {
		  const parsed = JSON.parse(s);
		  return Array.isArray(parsed) ? parsed : [];
		} catch(e) {
		  return [];
		}
	  }

	  // 3) что-то ещё странное
	  return [];
	}

    if (cursosReady) return;
    if (!tok()) return; // ждём общий вход
    cursosReady = true;
    // показать панель (её включает pills), но на всякий — снимем display:none
    const panel = document.getElementById('ui-cursos');
    if (panel) panel.style.display='';

    const esc = s => (s ?? '').toString().replace(/[&<>"]/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[m]));
    const normId = v => String(v ?? '').trim().replace(/\D+/g, '');

    // refs
    const tabForm   = $('#mzc-tab-form');
    const tabAssign = $('#mzc-tab-assign');
    const paneForm  = $('#mzc-pane-form');
    const paneAssign= $('#mzc-pane-assign');

    const tituloIn  = $('#mzc-cf-titulo');
    const codigoIn  = $('#mzc-cf-codigo');
    const modulosIn = $('#mzc-cf-modulos');
	const tipoIn    = $('#mzc-tipoform');
    const totalH    = $('#mzc-cf-total-horas');
    const totalM    = $('#mzc-cf-total-modulos');
    const cfMsg     = $('#mzc-cf-msg');
    const listBody  = $('#mzc-cf-list');

	const searchIn  = $('#mzc-cf-search');
	const searchMeta= $('#mzc-cf-search-meta');
	let cursosAll = [];

    const caCurso   = $('#mzc-ca-curso');
    const caCodigo  = $('#mzc-ca-codigo');
    const caMsg     = $('#mzc-ca-msg');
    const chipsBox  = $('#mzc-ca-teachers-chips');

    // parse + counters
	// parse + counters
	function parseModulesBasic(text){
	  const lines = (text || '')
		.split('\n')
		.map(l => l.trim())
		.filter(Boolean);

	  const mods = [];

	  // --- 1. первичный парс каждой строки ---
	  for (const line of lines){
		let name = line;
		let hours = 0;

		// 1.1 вытащим ЧАСЫ: (150 h) / (150 horas) / – 150 h / 150h / 150 horas
		// берём ПОСЛЕДНЕЕ совпадение в строке
		const matches = [...line.matchAll(/(\d+)\s*(?:h|horas?)/ig)];
		if (matches.length){
		  const m = matches[matches.length - 1]; // последняя пара "число + h/horas"
		  hours = parseInt(m[1], 10) || 0;
		}

		// 1.2 отрежем часы из названия
		// убираем варианты:
		// " – 150 horas", "- 150h", "(150 h)", "(150 horas)" в КОНЦЕ строки
		name = name.replace(/[\s–-]*\(?\d+\s*(?:h|horas?)\)?\s*$/i, '').trim();
		if (!name) name = 'Módulo';

		// 1.3 определяем код и тип (MF / UF / otro)
		let code = '';
		let kind = 'OTRO';

		const codeMatch = line.match(/^\s*((?:MF|UF)\d+[_-]?\d*)\b/i);
		if (codeMatch){
		  code = codeMatch[1].toUpperCase();
		}
		if (/^\s*MF\d+/i.test(line)) kind = 'MF';
		else if (/^\s*UF\d+/i.test(line)) kind = 'UF';

		mods.push({
		  name,
		  hours,
		  code,
		  kind,
		  raw: line
		});
	  }

	  // --- 2. группировка UF под MF и обнуление MF при совпадении суммы ---

	  // mfIndex -> { ufIndices:[], ufSum }
	  const mfGroups = new Map();
	  let currentMFIndex = -1;

	  mods.forEach((m, idx) => {
		if (m.kind === 'MF'){
		  currentMFIndex = idx;
		  if (!mfGroups.has(idx)){
			mfGroups.set(idx, { ufIndices: [], ufSum: 0 });
		  }
		  return;
		}
		if (m.kind === 'UF' && currentMFIndex >= 0){
		  const g = mfGroups.get(currentMFIndex) || { ufIndices: [], ufSum: 0 };
		  g.ufIndices.push(idx);
		  g.ufSum += (m.hours || 0);
		  mfGroups.set(currentMFIndex, g);
		}
	  });

	  // 2.2 проходим по MF и смотрим, совпадает ли сумма UF с часами MF
	  mfGroups.forEach((g, mfIdx) => {
		const mf = mods[mfIdx];
		const mfHours = mf.hours || 0;
		const ufSum = g.ufSum || 0;

		// Если у MF есть часы И есть UF, и их сумма ТОЧНО совпадает —
		// считаем, что MF — контейнер, и его часы надо обнулить.
		if (mfHours > 0 && ufSum > 0 && mfHours === ufSum){
		  mf.hours = 0;
		}
	  });

	  return mods;
	}


    function updateCounters(){
      const mods = parseModulesBasic(modulosIn.value);
      totalH.textContent = mods.reduce((s,m)=>s+m.hours,0);
      totalM.textContent = mods.length;
    }
    modulosIn.addEventListener('input', updateCounters);
    modulosIn.addEventListener('paste', ()=> setTimeout(updateCounters, 10));

    // tabs
    function setTab(which){
      const formActive = which === 'form';
      tabForm.classList.toggle('link', !formActive);
      tabAssign.classList.toggle('link', formActive);
      paneForm.style.display   = formActive ? 'block' : 'none';
      paneAssign.style.display = formActive ? 'none'  : 'block';
    }
    tabForm.onclick = ()=> setTab('form');
    tabAssign.onclick = async ()=>{
      setTab('assign');
      await loadAssignForm(true);
      if (caCurso.value) await updateAssignedTeachers();
    };
    setTab('form');

    // CRUD cursos
	$('#mzc-cf-save').onclick = async ()=>{
	  cfMsg.textContent=''; cfMsg.style.color='';
	  const titulo=(tituloIn.value||'').trim();
	  const codigo=(codigoIn.value||'').trim();
	  const raw   =(modulosIn.value||'').trim();

	  if (!titulo || !codigo){
		cfMsg.textContent='Título y código obligatorios';
		cfMsg.style.color='#b90e2e';
		return;
	  }

	  const modsParsed = parseModulesBasic(raw);
	  const modules = modsParsed.map(m => ({ name:m.name, hours:m.hours || 0 }));

	  if (!modules.length){
		cfMsg.textContent = 'Añade al menos una línea de módulo';
		cfMsg.style.color = '#b90e2e';
		return;
	  }

	  const payload = {
		codigo,
		titulo,
		modules,
		tipo_formacion: (tipoIn?.value || '')   // <-- было #mzc-cf-tipoform
	  };

	  if (editingId) {
		  payload.id = editingId;
		} else if (cloneFromCodigo) {
		  payload.clone_from = cloneFromCodigo; // ✅ NEW
		}


	  try{
		await apiJSON(`${API_A}/cursos/upsert${qs()}`, {
		  method:'POST',
		  headers:auth(true),
		  body:JSON.stringify(payload)
		});

		cfMsg.textContent='Guardado'; cfMsg.style.color='#0b6d22';
		cloneFromCodigo = null;
		await loadList();
		$('#mzc-cf-clear').click();
		editingId = null;
		cloneFromCodigo = null;
		document.dispatchEvent(new CustomEvent('mz:cursos-updated', { detail: { codigo } }));
	  }catch(e){
		cfMsg.textContent=e.message||'Error';
		cfMsg.style.color='#b90e2e';
	  }
	};

$('#mzc-cf-clear').onclick = ()=>{
  if (tipoIn) tipoIn.value = '';   
  editingId = null;
  tituloIn.value='';
  codigoIn.value='';
  modulosIn.value='';
  updateCounters();
};
function renderCursosTable(items){
        listBody.innerHTML='';
        if (!items.length){ listBody.innerHTML='<tr><td colspan="4">No hay cursos</td></tr>'; return; }
        for (const it of items){
		const tr = document.createElement('tr');
		tr.innerHTML = `
		  <td><strong>${esc(it.codigo)}</strong></td>
		  <td>${esc(it.titulo||'')}</td>
		  <td>${it.horas||0}</td>
		  <td class="mz-actions-col">
			<div class="mz-actions">
			  <button class="mz-btn link"
        data-edit
        data-action="admin.cursos.edit"
        aria-label="Editar"
        title="Editar">

				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				  <path d="M12 20h9"/>
				  <path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
				</svg>
			  </button>
			  <button class="mz-btn link"
        data-dup
        data-action="admin.cursos.duplicate"
        aria-label="Duplicar"
        title="Duplicar">

				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
				  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
				</svg>
			  </button>
			  <button class="mz-btn danger"
        data-delete
        data-action="admin.cursos.delete"
        aria-label="Eliminar"
        title="Eliminar">

				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				  <polyline points="3 6 5 6 21 6"/>
				  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
				  <path d="M10 11v6"/><path d="M14 11v6"/>
				  <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>
				</svg>
			  </button>
			</div>
		  </td>`;


// EDITAR
tr.querySelector('[data-edit]').onclick = ()=>{
  editingId = it.id;

  tituloIn.value = it.titulo || '';
  codigoIn.value = it.codigo || '';
  if (tipoIn) tipoIn.value = it.tipo_formacion || ''; 

  const mods = toModulesArray(it.modules);
  modulosIn.value = mods
    .map(m => `${m.name || ''} – ${m.hours || 0} horas`)
    .join('\n');

  updateCounters();
  cfMsg.textContent = '';
  setTab('form');
  window.scrollTo(0,0);
};


// DUPLICAR
const btnDup = tr.querySelector('[data-dup]');
if (btnDup){
  btnDup.onclick = ()=>{
    editingId = null;
	cloneFromCodigo = it.codigo; // ✅ NEW

    tituloIn.value = it.titulo || '';
	
    codigoIn.value = '';
    if (tipoIn) tipoIn.value = it.tipo_formacion || '';  // <-- было #mzc-cf-tipoform

    const mods = toModulesArray(it.modules);
    modulosIn.value = mods
      .map(m => `${m.name || ''} – ${m.hours || 0} horas`)
      .join('\n');

    updateCounters();
    setTab('form');

    cfMsg.textContent = 'Copia creada. Introduce un nuevo código para el curso.';
    cfMsg.style.color = '#0a5b93';

    window.scrollTo(0,0);
    codigoIn.focus();
  };
}


// ELIMINAR
tr.querySelector('[data-delete]').onclick = async ()=>{
  if (!confirm(`¿Eliminar curso "${it.titulo}" (${it.codigo})?`)) return;
  try{
    await apiJSON(`${API_A}/cursos/${it.id}/delete${qs()}`, {
      method:'POST',
      headers:auth(true)
    });
    cfMsg.textContent='Curso eliminado'; cfMsg.style.color='#0b6d22';
    await loadList();

    document.dispatchEvent(new CustomEvent('mz:cursos-updated', {
      detail: { deleted:true, id: it.id, codigo: it.codigo }
    }));
  }catch(e){
    cfMsg.textContent=e.message||'Error';
    cfMsg.style.color='#b90e2e';
  }
};


          listBody.appendChild(tr);
        }
      }

function applyCursosFilter(){
  const q = (searchIn?.value || '').trim().toLowerCase();
  const filtered = !q ? cursosAll : cursosAll.filter(it => {
    const codigo = (it.codigo || '').toLowerCase();
    const titulo = (it.titulo || '').toLowerCase();
    return codigo.includes(q) || titulo.includes(q);
  });

  renderCursosTable(filtered);

  if (searchMeta){
    searchMeta.textContent = !q
      ? `Mostrando ${cursosAll.length} curso(s).`
      : `Encontrados ${filtered.length} de ${cursosAll.length}.`;
  }
}
let tSearch = null;
if (searchIn){
  searchIn.addEventListener('input', ()=>{
    clearTimeout(tSearch);
    tSearch = setTimeout(applyCursosFilter, 80);
  });
}


async function loadList(){
  try{
    const j = await apiJSON(`${API_A}/cursos${qs(true)}`, {headers:auth()});
    cursosAll = (j.items || []);
    applyCursosFilter();
  }catch(_){
    listBody.innerHTML = '<tr><td colspan="4">Error</td></tr>';
  }
}


    // assign docentes
    function buildTeacherChips(teachers, assignedSet){
      chipsBox.replaceChildren();
      for (const t of (teachers||[])){
        const id = normId(t.user_id ?? t.uid ?? t.uid_str ?? t.id);
        if (!id) continue;
        const name = t.display_name || t.email || ('ID '+id);
        const btn = document.createElement('button');
        btn.type='button'; btn.className='mz-chip--block'; btn.dataset.id=id;
        btn.setAttribute('aria-pressed', assignedSet.has(id) ? 'true' : 'false');
        btn.innerHTML = `<i aria-hidden="true"></i><span>${esc(name)}</span>`;
        btn.addEventListener('click', ()=>{
          const on = btn.getAttribute('aria-pressed')==='true';
          btn.setAttribute('aria-pressed', on?'false':'true');
        });
        chipsBox.appendChild(btn);
      }
    }
	function getSelectedTeacherIdsFromChips(){
	  return [...chipsBox.querySelectorAll('.mz-chip--block[aria-pressed="true"]')]
		.map(b=>b.dataset.id)
		.filter(Boolean);
	}

    function renderAssignedBadges(enrolItems){
      const box = $('#mzc-ca-assigned');
      if (!Array.isArray(enrolItems)||!enrolItems.length){ box.innerHTML='No hay docentes asignados.'; return; }
      const chips = enrolItems.map(it=>{
        const name = (it.display_name || it.email || ('ID '+(it.uid_str || it.user_id))).toString();
        return `<span style="display:inline-block;border:1px solid #e6eef6;border-radius:10px;padding:3px 8px;margin:2px;background:#fbfdff">${name}</span>`;
      }).join(' ');
      box.innerHTML = `<div>Asignados ahora: ${chips}</div>`;
    }

    async function loadAssignForm(force=false){
      // cursos
      if (force || caCurso.options.length <= 1){
        try{
          const j = await apiJSON(`${API_A}/cursos${qs(true)}`, {headers:auth()});
          caCurso.innerHTML = '<option value="">— Selecciona curso —</option>';
          (j.items||[]).forEach(it=>{
            const opt=document.createElement('option');
            opt.value=it.codigo; opt.textContent=`${it.titulo} (${it.codigo})`;
            caCurso.appendChild(opt);
          });
        }catch(e){ console.error(e); }
      }
      // docentes
      let teachers = window.__MZ_CURSOS_TEACHERS__ || [];
      if (force || !teachers.length){
        try{
          const t = await apiJSON(`${API_A}/teachers${qs(true)}`, {headers:auth()});
          teachers = t.items || [];
          window.__MZ_CURSOS_TEACHERS__ = teachers;
        }catch(e){ console.error(e); teachers = []; }
      }
      buildTeacherChips(teachers, new Set());
    }

    async function updateAssignedTeachers(){
      const code = (caCurso.value||'').trim();
      caCodigo.value = code;
      const teachers = window.__MZ_CURSOS_TEACHERS__ || [];
      if (!code){ buildTeacherChips(teachers, new Set()); renderAssignedBadges([]); return; }
      const url = `${API_A}/enrolments${qs(true)}&codigo=${encodeURIComponent(code)}&role=teacher`;
      const { items=[] } = await apiJSON(url, {headers:auth(), cache:'no-store'});
      const assigned = new Set(items.map(it => normId(it.user_id ?? it.uid ?? it.uid_str ?? it.teacher_id)).filter(Boolean));
      buildTeacherChips(teachers, assigned);
      renderAssignedBadges(items);
    }

    caCurso.addEventListener('change', updateAssignedTeachers);
    $('#mzc-ca-reload').addEventListener('click', async ()=>{
      const sel = caCurso.value;
      await loadAssignForm(true);
      if (sel) caCurso.value = sel;
      await updateAssignedTeachers();
    });
    $('#mzc-ca-assign').addEventListener('click', async ()=>{
      const codigo = (caCurso.value||'').trim();
      if (!codigo){ caMsg.textContent='Selecciona un curso'; caMsg.style.color='#b90e2e'; return; }
      const teacherIds = getSelectedTeacherIdsFromChips();
      await apiJSON(`${API_A}/cursos/assign${qs()}`, {
        method:'POST', headers:auth(true),
        body:JSON.stringify({curso_codigo: codigo, teachers: teacherIds})
      });
      caMsg.textContent = `${teacherIds.length} profesor(es) asignados`;
      caMsg.style.color = '#0b6d22';
      await updateAssignedTeachers();
    });
document.dispatchEvent(new CustomEvent('mz:teachers-updated'));
    // init data
    loadList();
    updateCounters();
  }

  // 1) init сразу, если токен уже есть (перезагрузка)
  if (tok()) initCursosOnce();

  // 2) init при общем входе (из твоего shared gate)
  document.addEventListener('mz:admin-auth', (e)=>{ if (e?.detail?.ok) initCursosOnce(); });

  // 3) ленивый init при показе панели «Cursos» (из твоих pills)
  document.getElementById('ui-cursos')
    ?.addEventListener('mz:pane:show', (ev)=>{ if (ev?.detail?.mod==='cursos') initCursosOnce(); });
})();