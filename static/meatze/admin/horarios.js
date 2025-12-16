(()=>{ 'use strict';

  if (window.__MZ_HORARIOS_V5__) return;
  window.__MZ_HORARIOS_V5__ = true;

  const $ = s => document.querySelector(s);
const escapeHtml = (s) => (s ?? "").toString().replace(/[&<>"']/g, (m) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[m]));

  // === shared API/auth
  const API_BASE = ((window.wpApiSettings?.root)||'/').replace(/\/$/,'') + '/meatze/v5';
  const API_A = API_BASE + '/admin';
  const H = code => `/curso/${encodeURIComponent(code)}/horario`;
  const tok = () => sessionStorage.getItem('mz_admin') || '';
  const qs  = (bust=false)=> (tok()?`?adm=${encodeURIComponent(tok())}`:'') + (bust?(`${tok()?'&':'?'}_=${Date.now()}`):'');
  const auth= (isPost=false)=>{const h={}; if(tok()) h['X-MZ-Admin']=tok(); if(isPost) h['Content-Type']='application/json'; return h;};
async function apiJSON(url, opt={}) {
  const m = (opt.method || 'GET').toUpperCase();
  const r = await fetch(url, {...opt, cache:'no-store', headers:{...(opt.headers||{}), 'Cache-Control':'no-cache'}});

    const txt = await r.text(); let j=null;
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`); }
    if (!r.ok) throw new Error(j?.message || j?.code || `HTTP ${r.status}`);
    return j;
  }

  // === lazy panel init
  let initialized = false;
  function initOnce(){ if (initialized || !tok()) return; initialized = true; boot(); }

  // utils
  const pad2=n=>String(n).padStart(2,'0');
  const ymd = d => d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate());
  const addDays=(d,n)=>{const x=new Date(d); x.setDate(x.getDate()+n); return x;};
  const title=d=>d.toLocaleString('es-ES',{month:'long',year:'numeric'}).replace(/^./,c=>c.toUpperCase());

  const busy = {
    on(note){ $('#mzh-busytxt').textContent = note||''; $('#mzh-busybar').style.width='0%'; $('#mzh-busy').classList.add('show'); },
    off(){ $('#mzh-busy').classList.remove('show'); },
    pct(p){ $('#mzh-busybar').style.width = Math.max(0,Math.min(100,p)).toFixed(0)+'%'; }
  };

  // DOM
  const wrapAlumno = $('#mzh-alumno-wrap');
  const selAlumno  = $('#mzh-alumno');

  let alumnosById = new Map();
  const autoHoras     = $('#mzh-auto-horas');
  const autoHorasWrap = $('#mzh-auto-horas-wrap');
  const autoEnd       = $('#mzh-auto-end');
  const autoEndWrap   = $('#mzh-auto-end-wrap');

  const selCurso = $('#mzh-curso');
  const selTipo  = $('#mzh-tipo');
  const ctxInfo  = $('#mzh-ctx');
  const gTitle   = $('#mzh-title');
  const grid     = $('#mzh-grid');
  const legend   = $('#mzh-legend');
  const selCnt   = $('#mzh-selcnt');
  const btnPrev  = $('#mzh-prev');
  const btnNext  = $('#mzh-next');
	const autoNota = $('#mzh-auto-nota');
	const autoNotaWrap = $('#mzh-auto-nota-wrap');

  const btnAutoToggle = $('#mzh-auto-toggle'); // можно оставить, даже если кнопки нет
  const autoStart = $('#mzh-auto-start');
  const autoDesde = $('#mzh-auto-desde');
  const autoHasta = $('#mzh-auto-hasta');
  const autoAula  = $('#mzh-auto-aula');

  const autoSkipWE = $('#mzh-auto-skipweekend') || null;

  const autoSkipHol= $('#mzh-auto-skiphol');
    // чекбоксы дней недели L..D
  const dowInputs = {
    1: document.getElementById('mzh-dow-1'), // Lunes
    2: document.getElementById('mzh-dow-2'), // Martes
    3: document.getElementById('mzh-dow-3'), // Miércoles
    4: document.getElementById('mzh-dow-4'), // Jueves
    5: document.getElementById('mzh-dow-5'), // Viernes
    6: document.getElementById('mzh-dow-6'), // Sábado
    7: document.getElementById('mzh-dow-7'), // Domingo
	  };
	  
	    // Primer día especial
  const firstDaySpecial = $('#mzh-firstday-special');
  const firstDayWrap    = $('#mzh-firstday-wrap');
  const firstDayDesde   = $('#mzh-firstday-desde');
  const firstDayHasta   = $('#mzh-firstday-hasta');


	  // mapping: L=1→JS 1, ..., S=6→JS 6, D=7→JS 0
	  const dowMapToJS = {1:1,2:2,3:3,4:4,5:5,6:6,7:0};

	  function getAllowedDowsSet(){
		const set = new Set();

		for (let ui = 1; ui <= 7; ui++){
		  const el = dowInputs[ui];
		  if (el && el.checked){
			const jsDow = dowMapToJS[ui];
			if (jsDow !== undefined) set.add(jsDow);
		  }
		}
		if (!set.size){
		  [1,2,3,4,5].forEach(d => set.add(d));
		}
		if (autoSkipWE && autoSkipWE.checked){
		  set.delete(0); // Domingo
		  set.delete(6); // Sábado
		}

		return set;
	  }

  const autoRun  = $('#mzh-auto-run');
  const autoMsg  = $('#mzh-auto-msg');
  const btnExportGraphic = $('#mzh-export-graphic');
  const fixedToggle = $('#mzh-fixed-toggle');
  const fixedPanel  = $('#mzh-fixed-panel');
  const fixedY1     = $('#mzh-fixed-y1');
  const fixedY2     = $('#mzh-fixed-y2');
  const fixedY1Lbl  = $('#mzh-fixed-y1-label');
  const fixedY2Lbl  = $('#mzh-fixed-y2-label');
  const fixedSave   = $('#mzh-fixed-save');
  const fixedMsg    = $('#mzh-fixed-msg');
  const autoPanel = $('#mzh-auto-panel'); 
 //AlumnosPractica  
function pick(...vals){
  for (const v of vals){
    if (v == null) continue;
    const s = String(v).trim();
    if (s) return s;
  }
  return '';
}

function nameOfAlumno(it){
  const fullParts = [it.first_name, it.last_name1, it.last_name2].filter(Boolean).join(' ').trim();
  const fromNombre = [it.nombre, it.apellidos].filter(Boolean).join(' ').trim();
  return pick(
    fullParts,
    it.display_name,
    it.full_name,
    fromNombre,
    it.name
  ) || 'Alumno (sin nombre)';
}

function studentLabel(it){
  const fullParts = [it.first_name, it.last_name1, it.last_name2].filter(Boolean).join(' ').trim();
  const fromNombre = [it.nombre, it.apellidos].filter(Boolean).join(' ').trim();
  return pick(
    it.display_name,
    fullParts,
    it.full_name,
    fromNombre,
    it.name,
    it.email
  ) || String(it.user_id || it.id || '');
}


    function isAllowedByDOW(dateOrYmd, allowedSet){
		const d = (dateOrYmd instanceof Date)
		  ? dateOrYmd
		  : new Date(String(dateOrYmd) + 'T00:00:00');
		const dow = d.getDay(); // 0..6
		return allowedSet.has(dow);
	  }

  async function loadAlumnosForCurso(code){
    if (!selAlumno) return;
    selAlumno.innerHTML = '<option value="">— Todos —</option>';
    alumnosById.clear();
    if (!code) return;

    try{
      const j = await apiJSON(
        `${API_BASE}/curso/${encodeURIComponent(code)}/alumnos${qs(true)}`,
        { headers: auth() }
      );
      const list = j.items || [];
      list.forEach(it=>{
        const id = String(it.user_id);
        alumnosById.set(id, it);
        const o = document.createElement('option');
        o.value = id;
        o.textContent = nameOfAlumno(it);
        selAlumno.appendChild(o);
      });
    }catch(e){
      console.warn('No se pudo cargar alumnos:', e);
      const o = document.createElement('option');
      o.value = '';
      o.textContent = '(sin alumnos)';
      selAlumno.appendChild(o);
    }
  }
  
	function updateAmbitoUI(){
	  const isPractica = selTipo.value === 'practica';
	  if (wrapAlumno) {
		wrapAlumno.style.display = isPractica ? '' : 'none';
	  }
	  if (autoAula) {
		const lblSpan = autoAula.closest('label')?.querySelector('span');
		if (lblSpan) {
		  if (isPractica) {
			lblSpan.textContent = 'Nombre de la empresa';
			autoAula.placeholder = 'Nombre de la empresa…';
		  } else {
			lblSpan.textContent = 'Aula (opcional)';
			autoAula.placeholder = 'Aula…';
		  }
		}
	  }
	  if (autoNotaWrap)  autoNotaWrap.style.display  = isPractica ? '' : 'none';
	  if (autoHorasWrap) autoHorasWrap.style.display = isPractica ? '' : 'none';
	  if (autoEndWrap)   autoEndWrap.style.display   = isPractica ? '' : 'none';
	}

//End of alumnos

  let month = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
  let selected = new Set();
  let FIXED_NONLECTIVE = {};
  let FIXED_LOADED = false;

  async function loadFixedNonlective(force = false){
    if (FIXED_LOADED && !force) return;
    try{
      const j = await apiJSON(`${API_A}/fixed-nonlective${qs(true)}`, {headers:auth()});
      FIXED_NONLECTIVE = j.years || {};
    }catch(e){
      console.warn('fixed-nonlective load error', e);
      FIXED_NONLECTIVE = {};
    }
    FIXED_LOADED = true;
  }

	  function parseYearFieldExpanded(str, year){
		const out = [];
		const seen = new Set();
		const src = String(str || '');

		if (!src.trim()) return out;

		const addDate = (d) => {
		  const mm = String(d.getMonth()+1).padStart(2,'0');
		  const dd = String(d.getDate()).padStart(2,'0');
		  const key = `${dd}/${mm}`;
		  if (!seen.has(key)){
			seen.add(key);
			out.push(key);
		  }
		};

		const parts = src.split(',');
		for (const raw of parts){
		  const token = raw.trim();
		  if (!token) continue;

		  let m = /^(\d{1,2})\/(\d{1,2})\s*-\s*(\d{1,2})\/(\d{1,2})$/.exec(token);
		  if (m){
			const d1 = +m[1], mo1 = +m[2];
			const d2 = +m[3], mo2 = +m[4];
			const start = new Date(year, mo1-1, d1);
			const end   = new Date(year, mo2-1, d2);
			if (start <= end && start.getFullYear()===year && end.getFullYear()===year){
			  for (let d = new Date(start); d <= end; d.setDate(d.getDate()+1)){
				addDate(d);
			  }
			}
			continue;
		  }

		  m = /^(\d{1,2})\s*-\s*(\d{1,2})\/(\d{1,2})$/.exec(token);
		  if (m){
			const d1 = +m[1], d2 = +m[2], mo = +m[3];
			const start = new Date(year, mo-1, d1);
			const end   = new Date(year, mo-1, d2);
			if (start <= end && start.getFullYear()===year && end.getFullYear()===year){
			  for (let d = new Date(start); d <= end; d.setDate(d.getDate()+1)){
				addDate(d);
			  }
			}
			continue;
		  }
		  m = /^(\d{1,2})\/(\d{1,2})$/.exec(token);
		  if (m){
			const d = +m[1], mo = +m[2];
			const dt = new Date(year, mo-1, d);
			if (dt.getFullYear()===year && dt.getMonth()===(mo-1) && dt.getDate()===d){
			  addDate(dt);
			}
			continue;
		  }
		  console.warn('Formato de día no lectivo no reconocido:', token);
		}

		return out;
	  }

		function compressDateList(list) {
		  if (!Array.isArray(list) || !list.length) return "";

		  const year = new Date().getFullYear();
		  const dates = list.map(s => {
			const [dd, mm] = s.split('/');
			return new Date(year, +mm-1, +dd);
		  }).sort((a,b)=> a-b);

		  let out = [];
		  let start = dates[0];
		  let end = dates[0];

		  function fmt(d) {
			const dd = String(d.getDate()).padStart(2,'0');
			const mm = String(d.getMonth()+1).padStart(2,'0');
			return `${dd}/${mm}`;
		  }

		  for (let i=1; i<dates.length; i++){
			const d = dates[i];
			const prev = new Date(end);
			prev.setDate(prev.getDate()+1);

			if (d.getTime() === prev.getTime()) {
			  end = d;
			} else {
			  if (start.getTime() === end.getTime())
				out.push(fmt(start));
			  else
				out.push(`${fmt(start)}-${fmt(end)}`);

			  start = end = d;
			}
		  }
		  if (start.getTime() === end.getTime())
			out.push(fmt(start));
		  else
			out.push(`${fmt(start)}-${fmt(end)}`);

		  return out.join(', ');
		}

  async function saveFixedNonlective(yearMap){
    const r = await fetch(`${API_A}/fixed-nonlective${qs(true)}`, {
      method:'POST',
      headers:{...auth(true),'Content-Type':'application/json'},
      body: JSON.stringify({years:yearMap})
    });
    if (!r.ok){
      const t = await r.text().catch(()=> '');
      throw new Error(t || `HTTP ${r.status}`);
    }
    const j = await r.json().catch(()=>({}));
    FIXED_NONLECTIVE = j.years || {};
    FIXED_LOADED = true;
  }

  function fixedDatesBetween(startYMD, endYMD){
    const out = new Set();
    if (!startYMD || !endYMD || !FIXED_NONLECTIVE) return out;
    const s = new Date(startYMD+'T00:00:00');
    const e = new Date(endYMD+'T00:00:00');
    for (let y = s.getFullYear(); y <= e.getFullYear(); y++){
      const list = FIXED_NONLECTIVE[String(y)] || [];
      list.forEach(md=>{
        const [mm,dd] = String(md).split('-');
        if (!mm || !dd) return;
        const ymdStr = `${y}-${mm}-${dd}`;
        const d = new Date(ymdStr+'T00:00:00');
        if (d>=s && d<=e) out.add(ymdStr);
      });
    }
    return out;
  }

  let codigo = null;
  let cursoMeta = null;
  let cache = { map:new Map(), det:new Map(), keys:new Set() };
  let isDragging=false, dragAdd=true, anchor=null, dragPointerId=null;
  let cursosByCode = new Map();

	function getAlumnoGroupKey() {
	  if (!selAlumno) return '';

	  const raw = (selAlumno.value ?? '').trim();

	  // пусто → нет группы
	  if (!raw || raw === 'undefined' || raw === 'null') return '';

	  // если уже formato "alumno:XXX"
	  if (/^alumno:/.test(raw)) {
		const id = raw.slice(7).trim(); // после "alumno:"
		if (!id || id === 'undefined' || id === 'null') return '';
		return 'alumno:' + id;
	  }

	  // обычный ID → оборачиваем
	  return 'alumno:' + raw;
	}

function qp(){
  const p = new URLSearchParams();

  // ВСЕГДА фиксируем слой
  const tipo = (selTipo.value === 'practica') ? 'practica' : 'curso';
  p.set('tipo', tipo);

  if (tipo === 'practica') {
    const grupoKey = getAlumnoGroupKey();
    if (grupoKey) p.set('grupo', grupoKey);
  }

  const s = p.toString();
  return s ? ('?' + s) : '';
}




  function ymdFromDate(d){
    const pad2=n=>String(n).padStart(2,'0');
    return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
  }

  function normalizeDateStr(s, inputEl){
    if (inputEl && inputEl.type==='date' && inputEl.valueAsDate instanceof Date && !isNaN(inputEl.valueAsDate)){
      return ymdFromDate(inputEl.valueAsDate);
    }
    const txt = String(s||'').trim();
    if (!txt) return null;

    // 2) YYYY-MM-DD
    let m = /^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$/.exec(txt);
    if (m){
      const y=+m[1], mo=+m[2], d=+m[3];
      const dt = new Date(Date.UTC(y, mo-1, d));
      if (dt.getUTCFullYear()===y && (dt.getUTCMonth()+1)===mo && dt.getUTCDate()===d){
        const pad2=n=>String(n).padStart(2,'0');
        return `${y}-${pad2(mo)}-${pad2(d)}`;
      }
      return null;
    }

    // 3) DD-MM-YYYY (и варианты с / или .)
    m = /^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$/.exec(txt);
    if (m){
      const d=+m[1], mo=+m[2], y=+m[3];
      const dt = new Date(Date.UTC(y, mo-1, d));
      if (dt.getUTCFullYear()===y && (dt.getUTCMonth()+1)===mo && dt.getUTCDate()===d){
        const pad2=n=>String(n).padStart(2,'0');
        return `${y}-${pad2(mo)}-${pad2(d)}`;
      }
      return null;
    }

    return null;
  }

  async function boot(){
    await loadFixedNonlective();
    await loadCursos();
    wire();
  }

  function wire(){
    // смена курса
    selCurso.addEventListener('change', async ()=>{
      const code = selCurso.value;
      if (!code){
        codigo = null;
        cursoMeta = null;
        clearGrid();
        return;
      }
      const it = cursosByCode.get(code) || null;
      openCurso(code, it);
    });

    if (autoHoras){
      autoHoras.addEventListener('input', ()=> {
        if (selTipo.value === 'practica') {
          // поменяли часы → пересчитать дату конца
          updateAutoPreview();
        }
      });
    }

    if (autoEnd){
      autoEnd.addEventListener('change', recalcHorasFromEnd);
    }


    // смена ámbito (Curso / Práctica)
    selTipo.addEventListener('change', async ()=> {
      updateAmbitoUI();
      selected.clear();
      selCnt.textContent = '0';

      if (selTipo.value === 'practica' && codigo){
        await loadAlumnosForCurso(codigo);
      }
	const jumped = await autoJumpToFirstDate();
	if (!jumped) await renderMonth();

    });

    // смена ученика в режиме práctica
    if (selAlumno){
      selAlumno.addEventListener('change', ()=>{
        selected.clear();
        selCnt.textContent = '0';
  renderMonth();
  autoJumpToFirstDate();
      });
    }

    // стартовое состояние
    updateAmbitoUI();
    selCnt.textContent = '0';
    renderMonth();
    btnPrev.addEventListener('click', ()=>{
      month = new Date(month.getFullYear(), month.getMonth()-1, 1);
      renderMonth();
    });

    btnNext.addEventListener('click', ()=>{
      month = new Date(month.getFullYear(), month.getMonth()+1, 1);
      renderMonth();
    });

    if (btnExportGraphic) btnExportGraphic.addEventListener('click', exportWordGraphicAll);

    // === GLOBAL no lectivos centro (por año)
    if (fixedToggle && fixedPanel){
      fixedToggle.addEventListener('click', async ()=>{
        const now = new Date();
        const y1 = now.getFullYear();
        const y2 = y1 + 1;
        if (fixedY1Lbl) fixedY1Lbl.textContent = y1;
        if (fixedY2Lbl) fixedY2Lbl.textContent = y2;

        await loadFixedNonlective();
        const y1Arr = (FIXED_NONLECTIVE[String(y1)] || []).map(md=>{
          const [mm,dd] = md.split('-'); return `${dd}/${mm}`;
        });
        const y2Arr = (FIXED_NONLECTIVE[String(y2)] || []).map(md=>{
          const [mm,dd] = md.split('-'); return `${dd}/${mm}`;
        });
        if (fixedY1) fixedY1.value = compressDateList(y1Arr);
        if (fixedY2) fixedY2.value = compressDateList(y2Arr);

        fixedPanel.style.display =
          (fixedPanel.style.display === 'none' || !fixedPanel.style.display)
            ? 'block'
            : 'none';
      });
    }

    // автопанель всегда видна: сразу подтягиваем праздники и превью
    if (autoPanel) {
      (async ()=>{
        try{
          window.__MZ_HOLIDAYS_MAP__ = await loadHolidaysAndRenderList(autoStart.value || null);
          await updateAutoPreview();
        }catch(e){
          console.warn('No se pudo cargar vista previa de festivos:', e);
        }
      })();
    }

    if (fixedSave){
      fixedSave.addEventListener('click', async ()=>{
        fixedMsg.textContent = '';
        try{
          const now = new Date();
          const y1 = now.getFullYear();
          const y2 = y1 + 1;
          const map = {};

          const y1List = parseYearFieldExpanded(fixedY1?.value || '', y1);
          const y2List = parseYearFieldExpanded(fixedY2?.value || '', y2);

          map[String(y1)] = y1List.join(', ');
          map[String(y2)] = y2List.join(', ');

          await saveFixedNonlective(map);
          fixedMsg.textContent = 'Guardado correctamente para todos los cursos.';
          fixedMsg.style.color = '#0b6d22';
		  // авто-скрытие панели после сохранения
		if (fixedPanel) fixedPanel.style.display = 'none';

		// небольшой “успех” на кнопке (по желанию)
		if (fixedToggle){
		  const old = fixedToggle.textContent;
		  fixedToggle.textContent = 'Días no lectivos ✓';
		  setTimeout(()=>{ fixedToggle.textContent = old; }, 1200);
		}
          await updateAutoPreview();
        }catch(e){
          fixedMsg.textContent = 'Error al guardar: '+(e.message||'desconocido');
          fixedMsg.style.color = '#8a1233';
        }
      });
    }

    autoStart.addEventListener('change', async ()=>{
      window.__MZ_HOLIDAYS_MAP__ = await loadHolidaysAndRenderList(autoStart.value || null);
      await updateAutoPreview();
    });

    // переключатель "primer día especial"
    if (firstDaySpecial) {
      firstDaySpecial.addEventListener('change', ()=>{
        if (firstDayWrap) {
          firstDayWrap.style.display = firstDaySpecial.checked ? 'block' : 'none';
        }
        updateAutoPreview();
      });
    }

    ['input','change'].forEach(ev=>{
      if (autoDesde)   autoDesde.addEventListener(ev, updateAutoPreview);
      if (autoHasta)   autoHasta.addEventListener(ev, updateAutoPreview);
      if (autoSkipWE)  autoSkipWE.addEventListener(ev, updateAutoPreview);
      if (autoSkipHol) autoSkipHol.addEventListener(ev, updateAutoPreview);

      // если первый день особенный — его время тоже влияет
      if (firstDayDesde) firstDayDesde.addEventListener(ev, updateAutoPreview);
      if (firstDayHasta) firstDayHasta.addEventListener(ev, updateAutoPreview);

      Object.values(dowInputs).forEach(el=>{
        if (el) el.addEventListener(ev, updateAutoPreview);
      });
    });

    if (autoRun)   autoRun.addEventListener('click', autofillByModules);
  }

function renderHolList(items){
  const box = document.getElementById('mzh-hol-list');
  const badge = document.getElementById('mzh-hol-badge');
  if (!box || !badge) return;

  badge.textContent = String(items.length || 0);
  if (!items.length){
    box.innerHTML = '<div class="mz-help">—</div>';
    return;
  }

  // items: [{date:'2025-12-25', label:'Navidad', kind:'holiday'|'extra'|...}, ...]
  box.innerHTML = items.map(it => `
    <div class="mz-hol-item">
      <span class="d">${it.date}</span>
      <span class="r">— ${escapeHtml(it.label || '')}</span>
    </div>
  `).join('');
}

document.getElementById('mzh-tipo')?.addEventListener('change', updateStudentCard);
document.getElementById('mzh-alumno')?.addEventListener('change', updateStudentCard);
function setFinalDate(iso){
  const box = document.getElementById('mzh-final');
  const el = document.getElementById('mzh-final-date');
  if (!box || !el) return;
  if (!iso){ box.style.display='none'; return; }
  el.textContent = iso;
  box.style.display='block';
}

function updateStudentCard(){
  const tipo = document.getElementById('mzh-tipo')?.value;
  const card = document.getElementById('mzh-student-card');
  if (!card) return;

  if (tipo !== 'practica'){ card.style.display='none'; return; }

  const sel = document.getElementById('mzh-alumno');
  const id = sel?.value || '';
  const it = id ? (alumnosById.get(id) || null) : null;

  document.getElementById('mzh-student-name').textContent =
    it ? studentLabel(it) : (sel?.selectedOptions?.[0]?.textContent || '—');

  document.getElementById('mzh-student-email').textContent =
    it?.email || '—';

  card.style.display='block';
}



  // === Удаление многих дат одним запросом к /horario/bulk-delete
  async function deleteFechasBulk(codigo, fechas){
    if (!codigo || !fechas || !fechas.length) return {deleted:0};

	const tipo = (selTipo.value === 'practica') ? 'practica' : 'curso';
	const alumnoId  = (selAlumno && selAlumno.value)
	  ? selAlumno.value.trim()
	  : '';

		const payload = { fechas, tipo };

		if (tipo === 'practica') {
		  const grupoKey = getAlumnoGroupKey();
		  if (grupoKey) {
			payload.grupo = grupoKey;
		  }
		}


    return apiJSON(API_BASE + H(codigo) + '/bulk-delete' + qs(), {
      method: 'POST',
      headers: { ...auth(true) },
      body: JSON.stringify(payload)
    });
  }

  function clearGrid(){ grid.innerHTML=''; legend.innerHTML=''; gTitle.textContent='—'; }

	document.addEventListener('mz:cursos-updated', async (ev)=>{
	  const prevCode = selCurso.value || '';
	  const detail   = ev?.detail || {};
	  const newCode  = detail.codigo || prevCode || '';

	  await loadCursos();

	  if (newCode && cursosByCode.has(newCode)){
		selCurso.value = newCode;
		await openCurso(newCode, cursosByCode.get(newCode));
	  } else if (prevCode && cursosByCode.has(prevCode)){
		selCurso.value = prevCode;
	  }
	});

  async function loadCursos(){
    selCurso.innerHTML = '<option value="">Cargando…</option>';
    try{
      const j = await apiJSON(`${API_A}/cursos${qs(true)}`, {headers:auth()});
      const items = j.items || [];
      cursosByCode.clear();
      selCurso.innerHTML = '<option value="">— Selecciona curso —</option>';
      items.sort((a,b)=> (a.titulo||'').localeCompare(b.titulo||'','es',{sensitivity:'base'}) )
           .forEach(it=>{
              cursosByCode.set(it.codigo, it);
              const o=document.createElement('option');
              o.value=it.codigo; o.textContent = `${it.titulo} (${it.codigo})`;
              selCurso.appendChild(o);
           });
    }catch(_){ selCurso.innerHTML = '<option value="">Error</option>'; }
  }

	function infoCtx(){
	  const bits = [];
	  if (codigo) bits.push(codigo);

	  const isPractica = (selTipo.value === 'practica');
	  bits.push(isPractica ? 'práctica' : 'curso');

	  if (isPractica && selAlumno && selAlumno.value){
		const a = alumnosById.get(selAlumno.value);
		const label = a
		  ? nameOfAlumno(a)
		  : (selAlumno.options[selAlumno.selectedIndex]?.textContent || selAlumno.value);
		bits.push('alumno: ' + label);
	  }

	  if (cursoMeta?.localidad) bits.push(cursoMeta.localidad);
	  if (cursoMeta?.modalidad) bits.push(cursoMeta.modalidad);
	  if (cursoMeta?.fecha_inicio) bits.push((cursoMeta.fecha_inicio||'').slice(0,10));

	  ctxInfo.textContent = bits.filter(Boolean).join(' · ') || '—';
	}

	async function openCurso(code, meta){
	  codigo = code;
	  cursoMeta = meta || cursoMeta || null;

	  selected.clear();
	  selCnt.textContent='0';
	  infoCtx();

	  // === СБРОС СОСТОЯНИЯ AUTORRELLENAR ПРИ СМЕНЕ КУРСА ===
	  if (autoPanel){
		// очистить сообщение
		if (autoMsg){
		  autoMsg.textContent = '';
		  autoMsg.classList.remove('mz-err');
		}

		// очистить список праздников / статистику
		const holBox   = document.getElementById('mzh-hol-list');
		const holStats = document.getElementById('mzh-hol-stats');
		if (holBox)   holBox.innerHTML = '';
		if (holStats) holStats.textContent = '';

		// сбросить кэш festivos, чтобы подгружать по новому старту
		window.__MZ_HOLIDAYS_MAP__ = null;

		// дата начала по умолчанию — дата начала курса (если есть)
		if (autoStart){
		  if (cursoMeta?.fecha_inicio){
			autoStart.value = (cursoMeta.fecha_inicio || '').slice(0,10);
		  }else{
			autoStart.value = '';
		  }
		}
	  }

	  updateAmbitoUI();

	  if (selTipo.value === 'practica'){
	    await loadAlumnosForCurso(code);
	  }

	const jumped = await autoJumpToFirstDate();
	if (!jumped) await renderMonth();
	}
async function horarioMap(){
  if(!codigo) return {map:new Map(), keys:new Set(), det:new Map()};

  const wantTipo = (selTipo.value === 'practica') ? 'practica' : 'curso';
  const grupoKey = (wantTipo === 'practica') ? getAlumnoGroupKey() : '';

  // Собираем URL ДО любых console.log(url)
  const tipoQS = (wantTipo === 'practica')
    ? ('tipo=practica' + (grupoKey ? '&grupo=' + encodeURIComponent(grupoKey) : ''))
    : 'tipo=curso';

  const base = API_BASE + H(codigo);
  const url  = base + '?' + tipoQS + '&v=' + (Date.now()%1e9);

  const j = await apiJSON(url, {headers:auth()});

  const items = Array.isArray(j.items) ? j.items : [];
  const stat = items.reduce((a,x)=>{
    const t = (x.tipo||'').trim() || '(empty)';
    a[t] = (a[t]||0)+1;
    return a;
  }, {});
   const map=new Map(), keys=new Set(), det=new Map();

  items.forEach(it=>{
    const itTipo  = (it.tipo || '').trim() || 'curso'; // пустое считаем курсом
    const itGrupo = (it.grupo || '').trim();

    // 🔒 разделение слоёв
    if (wantTipo === 'curso') {
      if (itTipo === 'practica') return;
    } else {
      if (itTipo !== 'practica') return;
      if (grupoKey && itGrupo !== grupoKey) return;
    }

    const f=it.fecha;
    const d=(it.desde||'').slice(0,5);
    const h=(it.hasta||'').slice(0,5);
    if(!f || !d || !h) return;

    const k = d+'-'+h;
    keys.add(k);

    const arr=map.get(f)||[];
    if(!arr.includes(k) && arr.length<2) arr.push(k);
    map.set(f,arr);

    const list=det.get(f)||[];
    list.push({id:it.id, fecha:f, desde:it.desde, hasta:it.hasta, aula:(it.aula||''), nota:(it.nota||''), tipo:itTipo, grupo:itGrupo});
    det.set(f,list);
  });

  return {map, keys, det};
}


  const colorByKey = new Map();

  function hslToHex(h, s, l){
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2*l - 1)) * s;
    const x = c * (1 - Math.abs((h/60) % 2 - 1));
    const m = l - c/2;
    let r=0,g=0,b=0;
    if (0 <= h && h < 60)   { r=c; g=x; b=0; }
    else if (60 <= h && h <120){ r=x; g=c; b=0; }
    else if (120<= h && h <180){ r=0; g=c; b=x; }
    else if (180<= h && h <240){ r=0; g=x; b=c; }
    else if (240<= h && h <300){ r=x; g=0; b=c; }
    else                       { r=c; g=0; b=x; }

    const toHex = v => {
      const n = Math.round((v+m)*255);
      return n.toString(16).padStart(2,'0');
    };
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }

  function colorForKey(key){
    if (!colorByKey.has(key)){
      const idx = colorByKey.size;
      const hue = (idx*137.508) % 360;
      const hex = hslToHex(hue, 60, 85);
      colorByKey.set(key, hex);
    }
    return colorByKey.get(key);
  }

  async function renderMonth(){
    if(!codigo){ clearGrid(); return; }
    gTitle.textContent = title(month);
    grid.innerHTML=''; legend.innerHTML='';

    const f = new Date(month.getFullYear(), month.getMonth(), 1);
    const l = new Date(month.getFullYear(), month.getMonth()+1, 0);
    const start = (f.getDay()+6)%7;

    cache = await horarioMap();

    legend.innerHTML='';
    const mfSet = new Set();
    (cache.det||new Map()).forEach(items=>{
      items.forEach(it=>{
        const raw = (it.nota && it.nota.trim())
          ? it.nota.trim()
          : `${(it.desde||'').slice(0,5)}-${(it.hasta||'').slice(0,5)}`;
        const pure = String(raw).split(' · ')[0];
        mfSet.add(pure);
      });
    });
    [...mfSet].sort().forEach(k=>{
      const s = document.createElement('span');
      s.innerHTML = `<i style="background:${colorForKey(k)}"></i>${k}`;
      legend.appendChild(s);
    });

    for(let i=0;i<start;i++){ const c=document.createElement('div'); c.className='cell'; c.style.opacity='.3'; grid.appendChild(c); }

    for(let d=1; d<=l.getDate(); d++){
      const dt=new Date(f.getFullYear(), f.getMonth(), d);
      const key=ymd(dt);
		const el=document.createElement('div');
		el.className='cell';
		el.dataset.date=key;

		// ✅ новая разметка под CSS
		el.innerHTML = `<div class="day">${d}</div><div class="evts"></div>`;
		const evtsBox = el.querySelector('.evts');

      const dayItems = cache.det.get(key) || [];
      if (dayItems.length && evtsBox){
  // сортируем по времени
  dayItems.sort((a,b)=> (a.desde||'').localeCompare(b.desde||''));

  evtsBox.innerHTML = dayItems.slice(0,2).map(it=>{
    const t = `${(it.desde||'').slice(0,5)}–${(it.hasta||'').slice(0,5)}`;
    // label: nota или aula или пусто
    const label = (it.nota && it.nota.trim()) ? it.nota.trim() : (it.aula||'').trim();
    return `<div class="evtline"><span class="t">${t}</span>${label?` <span class="l">· ${escapeHtml(label)}</span>`:''}</div>`;
  }).join('');

  if (dayItems.length > 2){
    evtsBox.insertAdjacentHTML('beforeend', `<div class="evtextra">+${dayItems.length-2} más</div>`);
  }
}

	  
	  
	  if (dayItems.length){
        const mins = dayItems.map(it=>{
          const [h1,m1]=(it.desde||'').slice(0,5).split(':').map(Number);
          const [h2,m2]=(it.hasta||'').slice(0,5).split(':').map(Number);
          return Math.max(0,(h2*60+m2)-(h1*60+m1));
        });
        const total = Math.max(1, mins.reduce((a,b)=>a+b,0));
        let acc = 0;
        const stops = dayItems.map((it,i)=>{
          const rawKey = (it.nota && it.nota.trim()) ? it.nota.trim()
                       : `${(it.desde||'').slice(0,5)}-${(it.hasta||'').slice(0,5)}`;
          const pure = String(rawKey).split(' · ')[0];
          const c = colorForKey(pure);
          const from = (acc/total*100).toFixed(2)+'%';
          acc += mins[i];
          const to = (acc/total*100).toFixed(2)+'%';
          return `${c} ${from} ${to}`;
        });
        el.style.background = `linear-gradient(135deg, ${stops.join(', ')})`;
        el.title = dayItems.map(it => {
          const t = `${(it.desde||'').slice(0,5)}–${(it.hasta||'').slice(0,5)}`;
          return it.nota ? `${t} · ${it.nota}` : t;
        }).join('\n');
      }

      el.addEventListener('pointerdown', (e)=>{
        if (e.button!==0) return;
        e.preventDefault();
        if (e.shiftKey && anchor){ selectRange(anchor, key, true); return; }
        isDragging=true; dragPointerId=e.pointerId; anchor=key;
        dragAdd = !selected.has(key);
        toggleCell(key, dragAdd);
      });
      el.addEventListener('pointerenter', (e)=>{
        if (!isDragging || e.buttons!==1 || e.pointerId!==dragPointerId) return;
        toggleCell(key, dragAdd);
      });

      grid.appendChild(el);
    }
    window.addEventListener('pointerup', ()=>{ isDragging=false; dragPointerId=null; }, { once:true });
    refreshOutlines();
  }

  function refreshOutlines(){
    grid.querySelectorAll('[data-date]').forEach(el=>{
      el.style.outline = selected.has(el.dataset.date) ? '2px solid var(--mz-primary)' : '';
    });
  }
  function toggleCell(key, toAdd){
    const want = toAdd==null ? !selected.has(key) : !!toAdd;
    if (want) selected.add(key); else selected.delete(key);
    selCnt.textContent = selected.size;
    const el = grid.querySelector(`[data-date="${key}"]`);
    if (el) el.style.outline = selected.has(key) ? '2px solid var(--mz-primary)' : '';
  }
  function selectRange(a,b,toSelect){
    let d1=new Date(a), d2=new Date(b); if(d1>d2){ const t=d1; d1=d2; d2=t; }
    for(let d=new Date(d1); d<=d2; d=addDays(d,1)){
      const k=ymd(d); if(toSelect) selected.add(k); else selected.delete(k);
    }
    selCnt.textContent = selected.size;
    refreshOutlines();
  }

  // === Форматирование дат
  function esDateDMY(iso){
    if(!iso) return '—';
    const d = new Date((iso||'').slice(0,10)+'T00:00:00');
    if (isNaN(d)) return '—';
    const dd = String(d.getDate()).padStart(2,'0');
    const mm = String(d.getMonth()+1).padStart(2,'0');
    const yy = d.getFullYear();
    return `${dd}/${mm}/${yy}`;
  }

  // ---- FESTIVOS (sin clave): Nager.Date
	// Carga festivos ES-PV desde nuestro backend (кэш в WP)
	async function fetchFestivosESPVFull(year){
	  try{
		const url = `${API_A}/holidays/${year}${qs(true)}`;
		const r = await fetch(url, { cache:'no-store', headers: auth() });
		if (!r.ok) throw new Error(`HTTP ${r.status}`);

		const j = await r.json().catch(()=> ({}));
		const m = new Map();
		(j.items || []).forEach(h => {
		  if (!h.date) return;
		  m.set(h.date, (h.name || '').trim());
		});
		return m; // Map<YYYY-MM-DD, name>
	  }catch(e){
		console.warn('Festivos ES-PV (cache) no disponibles:', e);
		const statEl = document.getElementById('mzh-hol-stats');
		if (statEl) {
		  statEl.innerHTML = 'Festivos ES-PV no disponibles (cache).';
		}
		return new Map();
	  }
	}


  // Carga ES+PV con nombres; devuelve Map<date,name>
  async function loadHolidaysAndRenderList(baseDate){
    const d = baseDate ? new Date(baseDate+'T00:00:00') : new Date();
    const years = new Set([d.getFullYear(), d.getFullYear()+1]);
    const byDate = new Map();
    for (const y of years){
      try{
        const m = await fetchFestivosESPVFull(y);
        m.forEach((name, date)=> byDate.set(date, name));
      }catch(_){}
    }
    return byDate;
  }

  async function getHolidayMapForSpan(startYMD, endYMD){
    if (!startYMD || !endYMD) return new Map();
    const s = new Date(startYMD+'T00:00:00');
    const e = new Date(endYMD+'T00:00:00');
    const y1 = s.getFullYear(), y2 = e.getFullYear();
    const byDate = new Map();

    for (let y = y1; y <= y2; y++){
      try{
        const m = await fetchFestivosESPVFull(y);
        m.forEach((name, date)=>{
          const d = new Date(date+'T00:00:00');
          if (d >= s && d <= e){
            byDate.set(date, name);
          }
        });
      }catch(_){}
    }
    return byDate;
  }

  function ymdPlusOne(ymdStr){
    const d = new Date(ymdStr+'T00:00:00');
    d.setDate(d.getDate()+1);
    const y = d.getFullYear();
    const m = String(d.getMonth()+1).padStart(2,'0');
    const dd= String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${dd}`;
  }

  function buildVacacionesSegments(holMap, extrasSet, startYMD, endYMD){
    const omit = new Set();
    (holMap || new Map()).forEach((_name, date)=>{
      if (date >= startYMD && date <= endYMD) omit.add(date);
    });
    (extrasSet || new Set()).forEach(d=>{
      if (d >= startYMD && d <= endYMD) omit.add(d);
    });

    const arr = Array.from(omit).sort();
    if (!arr.length) return [];

    const segments = [];
    let segStart = arr[0];
    let segEnd   = arr[0];

    for (let i=1; i<arr.length; i++){
      const d = arr[i];
      if (d === ymdPlusOne(segEnd)){
        segEnd = d;
      }else{
        segments.push({from: segStart, to: segEnd});
        segStart = segEnd = d;
      }
    }
    segments.push({from: segStart, to: segEnd});

    const withMotivo = segments.map(seg=>{
      const holidaysInSeg = [];
      (holMap || new Map()).forEach((name, date)=>{
        if (date >= seg.from && date <= seg.to){
          holidaysInSeg.push((name || '').trim());
        }
      });

      let motivo = '';
      const uniqNames = Array.from(new Set(holidaysInSeg.filter(Boolean)));

      if (uniqNames.length === 1){
        motivo = `Vacaciones por ${uniqNames[0]}`;
      }else if (uniqNames.length > 1){
        const last = uniqNames.pop();
        motivo = `Vacaciones por ${uniqNames.join(', ')} y ${last}`;
      }else{
        motivo = 'Vacaciones (día no lectivo)';
      }

      return {
        from: seg.from,
        to:   seg.to,
        motivo
      };
    });

    return withMotivo;
  }

  function collectManualOmitFromCalendar(det, holMap, startYMD, endYMD){
    const res = new Set();
    if (!startYMD || !endYMD) return res;

    const hasHorario = new Set(det ? Array.from(det.keys()) : []);
    const s = new Date(startYMD + 'T00:00:00');
    const e = new Date(endYMD + 'T00:00:00');

    for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)){
      const y  = d.getFullYear();
      const m  = String(d.getMonth()+1).padStart(2,'0');
      const dd = String(d.getDate()).padStart(2,'0');
      const ymdStr = `${y}-${m}-${dd}`;

      const dow = d.getDay();
      const isWE = (dow === 0 || dow === 6);
      if (isWE) continue;

      if (holMap && holMap.has(ymdStr)) continue;

      if (!hasHorario.has(ymdStr)){
        res.add(ymdStr);
      }
    }
    return res;
  }

function renderHolidayListForPeriod(holMap, startYMD, endYMD, extrasSet){
  const box   = document.getElementById('mzh-hol-list');
  const statEl= document.getElementById('mzh-hol-stats');
  const badge = document.getElementById('mzh-hol-badge');
  if (!box) return;
    const s = new Date(startYMD+'T00:00:00');
    const e = new Date(endYMD+'T00:00:00');

    const holInRange = [];
    (holMap instanceof Map ? holMap : new Map()).forEach((name,date)=>{
      const dt = new Date(date+'T00:00:00');
      if (dt>=s && dt<=e) holInRange.push({date, name});
    });
    holInRange.sort((a,b)=> a.date.localeCompare(b.date));

    const extras = [];
    (extrasSet || new Set()).forEach(d=>{
      const dt = new Date(d+'T00:00:00');
      if (dt>=s && dt<=e) extras.push(d);
    });
    extras.sort();

    const groups = new Map();
    const ymOf = d => d.slice(0,7);
    holInRange.forEach(h=>{
      const ym = ymOf(h.date);
      if (!groups.has(ym)) groups.set(ym, {hol:[], extra:[]});
      groups.get(ym).hol.push(h);
    });
    extras.forEach(d=>{
      const ym = ymOf(d);
      if (!groups.has(ym)) groups.set(ym, {hol:[], extra:[]});
      groups.get(ym).extra.push(d);
    });

    const monthName = (ym) => {
      const [y,m] = ym.split('-').map(Number);
      return new Date(y, m-1, 1).toLocaleString('es-ES',{month:'long', year:'numeric'})
        .replace(/^./,c=>c.toUpperCase());
    };

    box.innerHTML = '';
    [...groups.keys()].sort().forEach(ym=>{
      const head = document.createElement('div');
      head.className = 'hol-month';
      head.textContent = monthName(ym);
      box.appendChild(head);

      const {hol, extra} = groups.get(ym);

      hol.forEach(h=>{
        const item = document.createElement('div');
        item.className = 'hol-item';
        item.textContent = `${h.date} — ${h.name || ''}`.trim();
        box.appendChild(item);
      });

      extra.forEach(d=>{
        const item = document.createElement('div');
        item.className = 'hol-item';
        item.textContent = `${d} — EXTRA (omitir)`;
        box.appendChild(item);
      });
    });

  // ✅ обновляем badge (праздники + extra)
  const total = (holInRange?.length || 0) + (extras?.length || 0);
  if (badge) badge.textContent = String(total);

  // ✅ обновляем стат-строку
  if (statEl){
    const parts = [];
    if (holInRange.length) parts.push(`Festivos: ${holInRange.length}`);
    if (extras.length)     parts.push(`Extra: ${extras.length}`);
    statEl.textContent = parts.join(' · ') || '—';
  }
}

  // ——— утилиты времени
  function parseHHMM(t){ const m=/^(\d{1,2}):(\d{2})$/.exec(String(t)||''); if(!m) return null;
    const h=Math.min(23,Math.max(0,+m[1])), mm=Math.min(59,Math.max(0,+m[2]));
    return [h,mm];
  }
  function minutesBetween(a,b){ const A=parseHHMM(a), B=parseHHMM(b); if(!A||!B) return 0; return (B[0]*60+B[1])-(A[0]*60+A[1]); }
  function addMinutes(base, mins){ const [h,m]=parseHHMM(base); const t=h*60+m+mins; const H=Math.floor((t%1440)/60), M=((t%60)+60)%60; return `${String(H).padStart(2,'0')}:${String(M).padStart(2,'0')}`; }

  function getAllModulesRaw(meta){
    let arr = [];
    try{
      const raw = typeof meta?.modules==='string' ? JSON.parse(meta.modules) : (meta?.modules||[]);
      if (Array.isArray(raw)) arr = raw;
    }catch(_){}
    return arr.map((x,i)=>({
      key: (x.code||x.cod||x.name||`M${i+1}`).toString(),
      horas: Number(x.hours||x.horas||0)
    }));
  }
  function getModulesGrouped(meta){
    let raw = [];
    try{
      raw = typeof meta?.modules === 'string'
        ? JSON.parse(meta.modules)
        : (meta?.modules || []);
    }catch(_){}

    const norm = (x,i)=>({
      key:   String(x.code || x.cod || x.name || `M${i+1}`),
      horas: Number(x.hours || x.horas || 0),
      label: String(x.name || x.titulo || x.title || x.code || x.cod || `M${i+1}`)
    });

    const list = (Array.isArray(raw) ? raw : []).map(norm);

    const MF_RE=/^MF/i, UF_RE=/^UF/i;
    let currentMF = null;

    return list.map(m=>{
      const isMF = MF_RE.test(m.key);
      const isUF = UF_RE.test(m.key);
      if (isMF) currentMF = m.key;
      return {
        ...m,
        type: isMF ? 'MF' : (isUF ? 'UF' : 'OTRO'),
        group: isMF ? m.key : (currentMF || m.key)
      };
    });
  }

  function horasByMF(meta){
    const grouped = getModulesGrouped(meta);
    const map = new Map();
    grouped.forEach(m=>{
      const g = m.group; const h = Math.max(0, m.horas||0);
      map.set(g, (map.get(g)||0) + h);
    });
    return map;
  }

  function getModules(meta){
    let arr = [];
    try{
      const raw = typeof meta?.modules==='string' ? JSON.parse(meta.modules) : (meta?.modules||[]);
      if (Array.isArray(raw)) arr = raw;
    }catch(_){}
    return arr.map((x,i)=>({
      key: (x.code||x.cod||x.name||`M${i+1}`).toString(),
      horas: Number(x.hours||x.horas||0)
    })).filter(x=>x.horas>0);
  }
  function totalCourseMinutes(meta){
    const mods = getModules(meta);
    return mods.reduce((s,m)=> s + Math.max(0, (m.horas||0)*60 ), 0);
  }
  const isWeekend = d => { const dow = d.getDay(); return dow===0 || dow===6; };
  function* daysFrom(startYMD){
    let d = new Date(startYMD+'T00:00:00');
    while(true){ yield d; d = new Date(d.getFullYear(), d.getMonth(), d.getDate()+1); }
  }

  function dayDiff(a,b){
    const da=new Date(a+'T00:00:00'), db=new Date(b+'T00:00:00');
    return Math.round((db-da)/86400000);
  }

	async function previewEndDate({startYMD, meta, desde, hasta, skipWE, skipHol, holSet, firstDay=null}){
	  const dayCapNormal = minutesBetween(desde, hasta);
	  if (dayCapNormal <= 0) return null;

	  let need = totalCourseMinutes(meta);
	  if (need <= 0) return null;

	  const firstCap = firstDay
		? minutesBetween(firstDay.desde || desde, firstDay.hasta || hasta)
		: null;

	  let holMap = holSet;
	  if (!holMap && skipHol){
		holMap = window.__MZ_HOLIDAYS_MAP__ || await loadHolidaysAndRenderList(startYMD);
		window.__MZ_HOLIDAYS_MAP__ = holMap;
	  }
	  holMap = holMap || new Map();

	  const startYear = (new Date(startYMD+'T00:00:00')).getFullYear();
	  const approxEnd = (startYear+1)+'-12-31';
	  const fixedApprox = fixedDatesBetween(startYMD, approxEnd);

	  const omit = new Set();
	  if (skipHol) holMap.forEach((_name, date)=> omit.add(date));
	  fixedApprox.forEach(d=> omit.add(d));

	  let usedDays = 0, skippedHolidays = 0, skippedWeekends = 0;
	  let lastDayYMD = startYMD;

	  const allowedDows = getAllowedDowsSet();
	  let isFirstDay = true;

	  for (const d of daysFrom(startYMD)){
		const ymdS = ymd(d);
		lastDayYMD = ymdS;

		if (!allowedDows.has(d.getDay())){
		  skippedWeekends++;
		  continue;
		}
		if (omit.has(ymdS)){
		  skippedHolidays++;
		  continue;
		}

		let capToday = dayCapNormal;
		if (isFirstDay && firstCap !== null){
		  capToday = firstCap;
		}

		if (need <= 0) break;

		const take = Math.min(capToday, need);
		need -= take;
		usedDays++;
		isFirstDay = false;

		if (need <= 0) break;
		if (dayDiff(startYMD, ymdS) > 730) break;
	  }

	  return {
		endYMD:lastDayYMD,
		usedDays,
		skippedHolidays,
		skippedWeekends,
		holSet:holMap
	  };
	}


async function previewPracticaByHoras(startYMD){
  const horasTotal = Number(autoHoras?.value || 0);
  if (!horasTotal || horasTotal <= 0) return null;

  const desde = autoDesde.value || '09:00';
  const hasta = autoHasta.value || '14:00';
  const dayCap = minutesBetween(desde, hasta);
  if (dayCap <= 0) return null;

  await loadFixedNonlective();

  let holMap = (autoSkipHol && autoSkipHol.checked)
    ? (window.__MZ_HOLIDAYS_MAP__ || await loadHolidaysAndRenderList(startYMD))
    : new Map();

  if (autoSkipHol && autoSkipHol.checked && !window.__MZ_HOLIDAYS_MAP__)
    window.__MZ_HOLIDAYS_MAP__ = holMap;

  const startYear = (new Date(startYMD+'T00:00:00')).getFullYear();
  const approxEnd = (startYear+1)+'-12-31';
  const fixedSet  = fixedDatesBetween(startYMD, approxEnd);

  const allowedDows = getAllowedDowsSet();

  let need = horasTotal * 60;
  let usedDays = 0, skippedHolidays = 0, skippedWeekends = 0;
  let lastDayYMD = startYMD;

  for (let d = new Date(startYMD+'T00:00:00'); need > 0; d = addDays(d, 1)){
    const ymdS = ymd(d);
    lastDayYMD = ymdS;

    const dow = d.getDay();
    if (!allowedDows.has(dow)){
      skippedWeekends++;
      continue;
    }
    if ((autoSkipHol && autoSkipHol.checked && holMap.has(ymdS)) || fixedSet.has(ymdS)){
      skippedHolidays++;
      continue;
    }

    const take = Math.min(dayCap, need);
    need -= take;
    usedDays++;

    if (dayDiff(startYMD, ymdS) > 730) break;
  }

  return {
    endYMD: lastDayYMD,
    usedDays,
    holMap,
    fixedSet,
    skippedHolidays,
    skippedWeekends
  };
}

  async function updateAutoPreview(){
    const start = autoStart.value || '';
    if (!start || !codigo) return;

    // --- MODO PRÁCTICA: duración fija en horas ---
    if (selTipo.value === 'practica'){
      const statEl = document.getElementById('mzh-hol-stats');
      const holBox = document.getElementById('mzh-hol-list');

      const res = await previewPracticaByHoras(start);
      if (!res){
        if (statEl) statEl.textContent = '';
        if (holBox) holBox.innerHTML = '';
        return;
      }

      // обновляем поле "Fin previsto"
      if (autoEnd) autoEnd.value = res.endYMD;

      // список праздников + extra
      renderHolidayListForPeriod(res.holMap, start, res.endYMD, res.fixedSet);

      if (statEl){
        const sDate = new Date(start+'T00:00:00');
        const eDate = new Date(res.endYMD+'T00:00:00');

        let holCount = 0;
        (res.holMap instanceof Map ? res.holMap : new Map()).forEach((_name,date)=>{
          const d = new Date(date+'T00:00:00');
          if (d>=sDate && d<=eDate) holCount++;
        });

        let extraCount = 0;
        (res.fixedSet || new Set()).forEach(d=>{
          const x = new Date(d+'T00:00:00');
          if (x>=sDate && x<=eDate) extraCount++;
        });

        const total = holCount + extraCount;

        statEl.innerHTML =
          `Festivos oficiales: ${holCount} · Días centro: ${extraCount} · Total omitidos: ${total} · ` +
          `<b>Fin de prácticas: ${res.endYMD}</b> ` +
          `(laborables: ${res.usedDays}, festivos saltados: ${res.skippedHolidays}, fines de semana saltados: ${res.skippedWeekends})`;
      }
      return;
    }

    // --- MODO CURSO (как было: по модулям) ---
    if (!cursoMeta) return;

    const desde = autoDesde.value || '09:00';
    const hasta = autoHasta.value || '14:00';
    const skipWE = autoSkipWE ? !!autoSkipWE.checked : false;
    const skipHol= !!autoSkipHol.checked;

    // спец. первый день
    const useFirst = firstDaySpecial && firstDaySpecial.checked;
    const fdDesde  = useFirst ? (firstDayDesde.value || desde) : null;
    const fdHasta  = useFirst ? (firstDayHasta.value || hasta) : null;

    await loadFixedNonlective();

    const res = await previewEndDate({
      startYMD: start,
      meta: cursoMeta,
      desde, hasta,
      skipWE, skipHol,
      holSet: window.__MZ_HOLIDAYS_MAP__,
      firstDay: useFirst ? {desde: fdDesde, hasta: fdHasta} : null
    });

    if (!res) return;

    const fixedSet = fixedDatesBetween(start, res.endYMD);
    renderHolidayListForPeriod(res.holSet, start, res.endYMD, fixedSet);

    const statEl = document.getElementById('mzh-hol-stats');
    if (statEl){
      const s = new Date(start+'T00:00:00');
      const e = new Date(res.endYMD+'T00:00:00');

      let holCount = 0;
      (res.holSet instanceof Map ? res.holSet : new Map()).forEach((_name,date)=>{
        const d = new Date(date+'T00:00:00');
        if (d>=s && d<=e) holCount++;
      });

      let extraCount = 0;
      fixedSet.forEach(d=>{
        const x = new Date(d+'T00:00:00');
        if (x>=s && x<=e) extraCount++;
      });

      const total = holCount + extraCount;

      statEl.innerHTML =
        `Festivos oficiales: ${holCount} · Días centro: ${extraCount} · Total omitidos: ${total} · ` +
        `<b>Fin estimado: ${res.endYMD}</b> ` +
        `(laborables: ${res.usedDays}, festivos saltados: ${res.skippedHolidays}, fines de semana saltados: ${res.skippedWeekends})`;
    }
  }

  let practicaSyncGuard = false;

  async function recalcHorasFromEnd(){
    if (practicaSyncGuard) return;
    if (selTipo.value !== 'practica') return;

    const start = autoStart.value || '';
    const end   = autoEnd?.value || '';
    if (!start || !end) return;

    const desde = autoDesde.value || '09:00';
    const hasta = autoHasta.value || '14:00';
    const dayCapMin = minutesBetween(desde, hasta);
    if (dayCapMin <= 0) return;

    practicaSyncGuard = true;
    try{
      await loadFixedNonlective();
      let holMap = autoSkipHol.checked
        ? (window.__MZ_HOLIDAYS_MAP__ || await loadHolidaysAndRenderList(start))
        : new Map();
      if (autoSkipHol.checked && !window.__MZ_HOLIDAYS_MAP__)
        window.__MZ_HOLIDAYS_MAP__ = holMap;

      const fixedSet = fixedDatesBetween(start, end);

      const s = new Date(start+'T00:00:00');
      const e = new Date(end+'T00:00:00');
      let totalHours = 0;

		const allowedDows = getAllowedDowsSet();

		for (let d = new Date(start+'T00:00:00'); d <= e; d = addDays(d, 1)){
		  const ymdS = ymd(d);
		  if (!isAllowedByDOW(d, allowedDows)) continue;
		  if ((autoSkipHol.checked && holMap.has(ymdS)) || fixedSet.has(ymdS)) continue;
		  totalHours += dayCapMin / 60;
		}


      if (autoHoras){
        autoHoras.value = Math.round(totalHours); // можно оставить дробью, если нужно
      }
    }finally{
      practicaSyncGuard = false;
    }
  }

  async function jumpCalendarTo(ymdStr){
    if (!ymdStr) return;
    const [y,m] = ymdStr.split('-').map(Number);
    if (!y || !m) return;
    month = new Date(y, m-1, 1);
    await renderMonth();
  }
  
async function autoJumpToFirstDate(){
  if (!codigo) return false;
  const { det } = await horarioMap();
  const dates = Array.from(det.keys()).sort();
  if (!dates.length) return false;
  const first = dates[0];
  await jumpCalendarTo(first);   // внутри уже renderMonth()
  return true;
}

	async function autofillByModules(){
	  autoMsg.textContent=''; autoMsg.classList.remove('mz-err');
	  if (!codigo){ autoMsg.textContent='Abre un curso.'; autoMsg.classList.add('mz-err'); return; }

	  const mods = getModulesGrouped(cursoMeta);
	  if (!mods.length){
		autoMsg.textContent='No hay módulos con horas en el curso.';
		autoMsg.classList.add('mz-err');
		return;
	  }
	      if (selTipo.value === 'practica'){
			  return autofillPracticas();
			}

      const useFirstDay = (selTipo.value === 'curso') && firstDaySpecial && firstDaySpecial.checked;

	  const start = autoStart.value || ([...selected].sort()[0]||'');
	  if (!start){
		autoMsg.textContent='Indica fecha de inicio o selecciona días.';
		autoMsg.classList.add('mz-err');
		return;
	  }

      if (useFirstDay && !autoStart.value){
        autoMsg.textContent = 'Para usar un primer día especial, indica la fecha de inicio.';
        autoMsg.classList.add('mz-err');
        return;
      }

	  const d1 = new Date(start+'T00:00:00');

	  await loadFixedNonlective();

	  // festivos / omit
	  const omit = new Set();
	  if (autoSkipHol.checked){
		let holMap = window.__MZ_HOLIDAYS_MAP__;
		if (!holMap) {
		  holMap = await loadHolidaysAndRenderList(start);
		  window.__MZ_HOLIDAYS_MAP__ = holMap;
		}
		holMap.forEach((_name, date)=> omit.add(date));
	  }

	  const startY = d1.getFullYear();
	  const approxEnd = (startY+1)+'-12-31';
	  fixedDatesBetween(start, approxEnd).forEach(d=> omit.add(d));

	  const desde = autoDesde.value || '09:00';
	  const hasta = autoHasta.value || '14:00';
	  const aula  = (autoAula.value||'').trim();
	  const notaBase = '';

	  const dayCapMin = minutesBetween(desde,hasta);
	  if (dayCapMin<=0){
		autoMsg.textContent='Rango horario inválido.';
		autoMsg.classList.add('mz-err');
		return;
	  }

      // настройки первого дня
		let firstDayCapMin = null;
		let firstDayDesdeStr = null;

		if (useFirstDay){
		  const fd = firstDayDesde ? (firstDayDesde.value || desde) : desde;
		  const fh = firstDayHasta ? (firstDayHasta.value || hasta) : hasta;

		  const cap = minutesBetween(fd, fh);
		  if (cap <= 0){
			autoMsg.textContent = 'Rango del primer día inválido.';
			autoMsg.classList.add('mz-err');
			return;
		  }

		  firstDayDesdeStr = fd;
		  firstDayCapMin   = cap;
		}

	  if (dayCapMin<=0){
		autoMsg.textContent='Rango horario inválido.';
		autoMsg.classList.add('mz-err');
		return;
	  }

      let datesQueue;
      const allowedDows = getAllowedDowsSet();

      if (useFirstDay){
        datesQueue = [];
      }else{
        datesQueue = [...selected].sort();
      }

	  let dayCursor = new Date(d1);

		function nextDate(){
		  if (datesQueue.length) return datesQueue.shift();
		  while(true){
			const ymdS = ymd(dayCursor);
			if (!isAllowedByDOW(dayCursor, allowedDows)){
			  dayCursor = addDays(dayCursor,1);
			  continue;
			}
			if (omit.has(ymdS)){
			  dayCursor = addDays(dayCursor,1);
			  continue;
			}
			const res = ymdS;
			dayCursor = addDays(dayCursor,1);
			return res;
		  }
		}

	  const plan = []; // {fecha, desde, hasta, aula, nota}
	  let modIdx = 0, modRestMin = mods[0].horas*60;
	  let cur = { fecha:null, leftMin:0, tFrom:desde };
      let firstDayUsed = false;

	  function pushSpan(fecha, t1, t2, key, groupKey){
		const label = key;
		const nota = groupKey + (notaBase?` · ${notaBase}`:'') + ` · ${label}`;
		plan.push({fecha, desde:t1, hasta:t2, aula, nota});
	  }

	  while (modIdx < mods.length){
		if (!cur.fecha){
		  cur.fecha = nextDate();

          if (useFirstDay && !firstDayUsed){
            // первый день – особый диапазон
            cur.leftMin = firstDayCapMin;
            cur.tFrom   = firstDayDesdeStr || desde;
            firstDayUsed = true;
          }else{
		    cur.leftMin = dayCapMin;
		    cur.tFrom   = desde;
          }
		}

		// если день по ошибке попал в omit (из выделения)
		if (autoSkipHol.checked && omit.has(cur.fecha)){
		  cur.fecha = null;
		  continue;
		}

		const take = Math.min(cur.leftMin, modRestMin);
		const t2 = addMinutes(cur.tFrom, take);
		const mfKey = mods[modIdx].group || mods[modIdx].key;
		pushSpan(cur.fecha, cur.tFrom, t2, mods[modIdx].key, mfKey);
		cur.leftMin -= take;
		modRestMin  -= take;
		cur.tFrom = t2;

		if (modRestMin<=0){
		  modIdx++;
		  if (modIdx<mods.length) modRestMin = mods[modIdx].horas*60;
		}
		if (cur.leftMin<=0){
		  cur.fecha=null; // следующий день
		}
	  }

	  // === ВАЖНО: ПОЛНАЯ ОЧИСТКА ПЕРЕД ЗАПИСЬЮ ПЛАНА ===
	  busy.on('Autorrellenando…');
	  try{
		// 1) загрузить текущее расписание и удалить все даты для этого curso/ámbito/grupo
		const { det } = await horarioMap();
		const fechasExistentes = Array.from(det.keys());
		if (fechasExistentes.length){
		  await deleteFechasBulk(codigo, fechasExistentes);
		}

		// 2) теперь записать ПОЛНОСТЬЮ новое расписание
		const fechasPlan = [...new Set(plan.map(x=>x.fecha))].sort();

await apiJSON(API_BASE + H(codigo) + qp(), {
  method:'POST',
  headers:{...auth(true)},
  body: JSON.stringify({items: plan})
});


		// 3) обновить fecha_inicio
		const newStart = fechasPlan[0] || (autoStart.value || '');
		if (newStart){
		  try{
			await apiJSON(`${API_A}/curso/${encodeURIComponent(codigo)}/fecha_inicio${qs()}`, {
			  method:'POST',
			  headers:{...auth(true)},
			  body: JSON.stringify({fecha:newStart})
			});
			if (cursoMeta) { cursoMeta = {...cursoMeta, fecha_inicio:newStart}; infoCtx(); }
		  }catch(_){}
		}

		autoMsg.textContent = `Añadido: ${plan.length} franjas en ${fechasPlan.length} día(s).`;
		autoMsg.classList.remove('mz-err');
		selected.clear(); selCnt.textContent='0';
		await renderMonth();
	  }catch(e){
		autoMsg.textContent = 'Error: '+(e.message||'desconocido');
		autoMsg.classList.add('mz-err');
	  }finally{
		busy.off();
	  }
	}

	  async function autofillPracticas(){
		autoMsg.textContent = '';
		autoMsg.classList.remove('mz-err');

		if (!codigo){
		  autoMsg.textContent = 'Abre un curso.';
		  autoMsg.classList.add('mz-err');
		  return;
		}

		const grupoKey = getAlumnoGroupKey();
		if (!grupoKey){
		  autoMsg.textContent = 'Selecciona un alumno para las prácticas.';
		  autoMsg.classList.add('mz-err');
		  return;
		}


		const start = autoStart.value || '';
		if (!start){
		  autoMsg.textContent = 'Indica fecha de inicio.';
		  autoMsg.classList.add('mz-err');
		  return;
		}

		const horas = Number(autoHoras?.value || 0);
		if (!horas || horas <= 0){
		  autoMsg.textContent = 'Indica la duración total en horas.';
		  autoMsg.classList.add('mz-err');
		  return;
		}

		const desde = autoDesde.value || '09:00';
		const hasta = autoHasta.value || '14:00';
		const dayCapMin = minutesBetween(desde, hasta);
		if (dayCapMin <= 0){
		  autoMsg.textContent = 'Rango horario inválido.';
		  autoMsg.classList.add('mz-err');
		  return;
		}

		await loadFixedNonlective();

		let holMap = autoSkipHol.checked
		  ? (window.__MZ_HOLIDAYS_MAP__ || await loadHolidaysAndRenderList(start))
		  : new Map();
		if (autoSkipHol.checked && !window.__MZ_HOLIDAYS_MAP__)
		  window.__MZ_HOLIDAYS_MAP__ = holMap;

		const startYear = (new Date(start+'T00:00:00')).getFullYear();
		const approxEnd = (startYear+1)+'-12-31';
		const fixedSet  = fixedDatesBetween(start, approxEnd);

		const omit = new Set();
		if (autoSkipHol.checked) holMap.forEach((_n, date)=> omit.add(date));
		fixedSet.forEach(d=> omit.add(d));

		const aula = (autoAula.value || '').trim();
		const notaDir = (autoNota?.value || '').trim();

		const allowedDows = getAllowedDowsSet();
		let skippedWeekends = 0, skippedHolidays = 0;

		let need = horas * 60;
		const plan = [];
		let d = new Date(start+'T00:00:00');
		let lastYMD = start;


		while (need > 0){
		  const ymdS = ymd(d);
		  lastYMD = ymdS;

		  const dow = d.getDay();
		  if (!allowedDows.has(dow)){
			skippedWeekends++;
			d = addDays(d,1);
			continue;
		  }
		  if (omit.has(ymdS)){
			skippedHolidays++;
			d = addDays(d,1);
			continue;
		  }

		  const take = Math.min(dayCapMin, need);
		  const t1 = desde;
		  const t2 = addMinutes(desde, take);

		  plan.push({
			fecha: ymdS,
			desde: t1,
			hasta: t2,
			  aula,
			  nota: notaDir
		  });

		  need -= take;
		  d = addDays(d,1);

		  if (dayDiff(start, ymdS) > 730) break;
		}

		if (!plan.length){
		  autoMsg.textContent = 'No se pudo generar ningún día de prácticas.';
		  autoMsg.classList.add('mz-err');
		  return;
		}

		busy.on('Autorrellenando prácticas…');
		try{
		  // 1) чистим только текущий ámbito/grupo (у тебя уже есть deleteFechasBulk с tipo=practica + grupo=alumno:ID)
		  const { det } = await horarioMap();
		  const fechasExistentes = Array.from(det.keys());
		  if (fechasExistentes.length){
			await deleteFechasBulk(codigo, fechasExistentes);
		  }
		await apiJSON(
		  API_BASE + H(codigo) + '?tipo=practica&grupo=' + encodeURIComponent(grupoKey),
		  {
			method:'POST',
			headers:{...auth(true)},
			body: JSON.stringify({items: plan})
		  }
		);


		  if (autoEnd) autoEnd.value = lastYMD;

		  autoMsg.textContent =
			`Prácticas generadas: ${plan.length} franjas en ${new Set(plan.map(p=>p.fecha)).size} día(s) (fin: ${lastYMD}).`;
		  autoMsg.classList.remove('mz-err');

		  selected.clear();
		  selCnt.textContent = '0';
		  await renderMonth();
	
		}catch(e){
		  autoMsg.textContent = 'Error: '+(e.message||'desconocido');
		  autoMsg.classList.add('mz-err');
		}finally{
		  busy.off();
		}
	  }

  // 1) init сразу, если токен уже есть
  if (tok()) initOnce();

  // 2) init при общем входе (shared gate)
  document.addEventListener('mz:admin-auth', (e)=>{ if (e?.detail?.ok) initOnce(); });

  // 3) ленивый init при показе панели «Horarios»
  document.getElementById('ui-horarios')
    ?.addEventListener('mz:pane:show', (ev)=>{ if (ev?.detail?.mod==='horarios') initOnce(); });

  // === Экспорт (месяцы, легенда, DOCX) ===

  function esMonthTitle(y, m){
    return new Date(y, m-1, 1)
      .toLocaleString('es-ES', {month:'long', year:'numeric'})
      .replace(/^./, c=>c.toUpperCase());
  }
  function esDowShort(i){
    return ['L','M','X','J','V','S','D'][i-1];
  }

  function monthsFromDet(det){
    const set = new Set();
    (det ? Array.from(det.keys()) : []).forEach(d=>{
      set.add(d.slice(0,7));
    });
    return Array.from(set).sort();
  }

  function buildMonthSVG(ym, detForMonth, keyColor){
    const [y, m] = ym.split('-').map(Number);
    const first = new Date(y, m-1, 1);
    const last  = new Date(y, m, 0);
    const startOffset = (first.getDay()+6)%7;

    const pad   = 18;
    const headH = 42;
    const cellW = 64;
    const cellH = 36;
    const gap   = 6;

    const cols = 7, rows = 6;
    const w = pad*2 + cols*cellW + (cols-1)*gap;
    const h = pad*2 + headH + rows*cellH + (rows-1)*gap + 16;

    const xOf = c => pad + c*(cellW+gap);
    const yOf = r => pad + headH + r*(cellH+gap);

    let cells = [];
    for(let r=0;r<rows;r++){
      for(let c=0;c<cols;c++){
        const idx = r*cols + c;
        const day = idx - startOffset + 1;
        const inMonth = day>=1 && day<=last.getDate();
        const ymdStr = inMonth ? `${y}-${String(m).padStart(2,'0')}-${String(day).padStart(2,'0')}` : null;
        const items = inMonth ? (detForMonth.get(ymdStr)||[]) : [];
        cells.push({r,c,day,inMonth,ymdStr,items});
      }
    }

    let defs = [];
    let rects = [];
    let labels = [];

    const minsBetweenSafe = (a,b)=>{
      const [h1,mi1]=a.slice(0,5).split(':').map(Number);
      const [h2,mi2]=b.slice(0,5).split(':').map(Number);
      return Math.max(0,(h2*60+mi2)-(h1*60+mi1));
    };

    cells.forEach((cell, i)=>{
      const idBase = `g${ym.replace('-','')}_${cell.ymdStr||('x'+i)}`;
      const x = xOf(cell.c), y = yOf(cell.r);

      rects.push(
        `<rect x="${x}" y="${y}" rx="10" ry="10" width="${cellW}" height="${cellH}" ` +
        `fill="${cell.inMonth ? '#f8fafc':'#f1f5f9'}" stroke="#000000" stroke-width="1"/>`
      );

      if (cell.inMonth && cell.items.length){
        const parts = cell.items.slice().sort((a,b)=> String(a.desde).localeCompare(String(b.desde)));
        const mins = parts.map(it=> minsBetweenSafe(it.desde, it.hasta));
        const total = Math.max(1, mins.reduce((s,v)=>s+v,0));
        const gid = `${idBase}`;

        let accMins = 0;
        const stopsArr = [];
        parts.forEach((it, idx) => {
          const raw = (it.nota && it.nota.trim())
            ? it.nota.trim()
            : `${(it.desde||'').slice(0,5)}-${(it.hasta||'').slice(0,5)}`;
          const pure = String(raw).split(' · ')[0];
          const color = keyColor(pure);

          const seg = mins[idx];
          const fromPct = (accMins / total * 100);
          const toPct   = ((accMins + seg) / total * 100);
          accMins += seg;

          stopsArr.push([fromPct, color], [toPct, color]);
        });

        defs.push(
          `<linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1">` +
            stopsArr.map(([pct, col]) =>
              `<stop offset="${pct.toFixed(2)}%" stop-color="${col}"/>`
            ).join('') +
          `</linearGradient>`
        );

        rects.push(
          `<rect x="${x}" y="${y}" rx="10" ry="10" width="${cellW}" height="${cellH}" fill="url(#${gid})" stroke="none"/>`
        );
      }

      const dayLbl = (cell.inMonth && cell.day>=1) ? cell.day : '';
      labels.push(
        `<text x="${x+10}" y="${y+24}" font-size="22" font-weight="700" ` +
        `fill="#000000">${dayLbl}</text>`
      );
    });

    const head = [];
    for (let c = 0; c < cols; c++) {
      head.push(
        `<text x="${xOf(c)+cellW/2}" y="${pad+16}" text-anchor="middle" ` +
        `font-size="12" fill="#000000">${esDowShort(c+1)}</text>`
      );
    }

    const monthTitle = esMonthTitle(y,m);

    return `
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <defs>${defs.join('')}</defs>
  <rect x="0" y="0" width="${w}" height="${h}" fill="#ffffff"/>
  <text x="${pad}" y="${pad+4}" font-size="24" font-weight="700"
        fill="#142333" stroke="#000000" stroke-width="0.6" paint-order="stroke">
    ${monthTitle}
  </text>
  ${head.join('')}
  ${rects.join('')}
  ${labels.join('')}
</svg>`;
  }

  function svgSize(svg){
    const w = +(/width="([\d.]+)"/.exec(svg)?.[1] || 0);
    const h = +(/height="([\d.]+)"/.exec(svg)?.[1] || 0);
    if (w && h) return {w,h};
    const vb = /viewBox="[^"]*?(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)/.exec(svg);
    if (vb) return {w:+vb[3], h:+vb[4]};
    return {w:1200, h:800};
  }

  function svgToRasterDataUrl(svg, { scale=1.5, mime='image/jpeg', quality=0.92 } = {}) {
    return new Promise((resolve, reject) => {
      const {w,h} = svgSize(svg);
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas');
        c.width  = Math.max(1, Math.round(w*scale));
        c.height = Math.max(1, Math.round(h*scale));
        const ctx = c.getContext('2d', {alpha:false});
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.setTransform(scale,0,0,scale,0,0);
        ctx.drawImage(img, 0, 0);
        try {
          resolve(c.toDataURL(mime, quality));
        } catch(e) {
          reject(e);
        }
      };
      img.onerror = e => reject(e?.error||new Error('img load failed'));
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    });
  }

  async function exportWordGraphicAll(){
    try{
      if (!codigo){ alert('Abre un curso primero.'); return; }
      busy.on('Generando DOCX…');

      const esc = s => String(s||'').replace(/[&<>]/g, c =>
        c==='&'?'&amp;':c==='<'?'&lt;':'&gt;'
      );

      cache = await horarioMap();
      const det = cache.det || new Map();
      const allDates = Array.from(det.keys()).sort();
      const cursoStart = allDates[0] || (cursoMeta?.fecha_inicio || '');
      const cursoEnd   = allDates[allDates.length-1] || '';

      let vacacionesSegs = [];
      if (cursoStart && cursoEnd){
        const holMap = await getHolidayMapForSpan(cursoStart, cursoEnd);
        await loadFixedNonlective();
        const fixedSet = fixedDatesBetween(cursoStart, cursoEnd);
        const manualOmit = collectManualOmitFromCalendar(cache.det, holMap, cursoStart, cursoEnd);
        manualOmit.forEach(d => fixedSet.add(d));
        vacacionesSegs = buildVacacionesSegments(holMap, fixedSet, cursoStart, cursoEnd);
      }

      const groupedAll = getModulesGrouped(cursoMeta);
      const horasMF    = horasByMF(cursoMeta);
      const mfByModuleKey = new Map();
      groupedAll.forEach(m => {
        const mf = (m.type === 'MF') ? m.key : (m.group || null);
        if (!mf) return;
        mfByModuleKey.set(m.key, mf);
      });

      const modsAll = groupedAll.map(m=>({
        key:   m.key,
        label: m.label || m.key,
        horas: Number(m.horas||0),
        type:  m.type,
        group: m.group
      }));
      const moduleKeySet = new Set(modsAll.map(m=>m.key));
      // horas por UF y horas de cada MF calculadas SOLO por sus UF hijas
      const horasPorUF = new Map();
      const horasMFDesdeUF = new Map();

      modsAll.forEach(m => {
        const h = Number(m.horas || 0) || 0;
        if (m.type === 'UF') {
          horasPorUF.set(m.key, h);
          if (m.group) {
            horasMFDesdeUF.set(m.group, (horasMFDesdeUF.get(m.group) || 0) + h);
          }
        }
      });

      function normHHMM(t){
        const m = /^(\d{1,2}):(\d{2})/.exec(String(t)||'');
        if(!m) return null;
        const h = Math.min(23,Math.max(0,+m[1]));
        const mm= Math.min(59,Math.max(0,+m[2]));
        return String(h).padStart(2,'0') + ':' + String(mm).padStart(2,'0');
      }
      function minTime(a,b){ if(!a) return b; if(!b) return a; return a<b ? a : b; }
      function maxTime(a,b){ if(!a) return b; if(!b) return a; return a>b ? a : b; }

      const moduleDateRangeMF  = new Map();
      const moduleTimeInfoMF   = new Map();
      const moduleDateRangeMod = new Map();
      const moduleTimeInfoMod  = new Map();

      function ensureTimeInfo(map, key){
        let ti = map.get(key);
        if (!ti){
          ti = {minStart:null, maxEnd:null, spansByDate:new Map()};
          map.set(key, ti);
        }
        return ti;
      }

      function extractModuleKeyFromNota(raw){
        const txt = String(raw||'').trim();
        if (!txt) return null;
        const parts = txt.split(' · ').map(t=>t.trim()).filter(Boolean);
        for (let i=parts.length-1; i>=0; i--){
          const p = parts[i];
          if (moduleKeySet.has(p)) return p;
          if (/^(MF|UF)\w+/i.test(p)) return p;
        }
        return parts[parts.length-1] || parts[0] || null;
      }

      det.forEach((items, ymdDate)=>{
        items.forEach(it=>{
          const rawNota = (it.nota && it.nota.trim())
            ? it.nota.trim()
            : `${(it.desde||'').slice(0,5)}-${(it.hasta||'').slice(0,5)}`;

          const modKeyFromNota = extractModuleKeyFromNota(rawNota);
          const mfKey = mfByModuleKey.get(modKeyFromNota || '') || (
            String(rawNota).split(' · ')[0]
          );
          if (!mfKey) return;

          const d = normHHMM(it.desde);
          const h = normHHMM(it.hasta);
          if (!d || !h) return;

          {
            let r = moduleDateRangeMF.get(mfKey);
            if (!r) {
              r = { start: ymdDate, end: ymdDate };
              moduleDateRangeMF.set(mfKey, r);
            } else {
              if (ymdDate < r.start) r.start = ymdDate;
              if (ymdDate > r.end)   r.end   = ymdDate;
            }

            const ti = ensureTimeInfo(moduleTimeInfoMF, mfKey);
            ti.minStart = minTime(ti.minStart, d);
            ti.maxEnd   = maxTime(ti.maxEnd, h);
            const spans = ti.spansByDate.get(ymdDate) || [];
            spans.push([d,h]);
            spans.sort((A,B)=>A[0].localeCompare(B[0]));
            const merged = [];
            for (const s of spans){
              if (!merged.length){ merged.push(s); continue; }
              const last = merged[merged.length-1];
              if (last[1] >= s[0]){
                if (s[1] > last[1]) last[1] = s[1];
              } else {
                merged.push(s);
              }
            }
            ti.spansByDate.set(ymdDate, merged);
          }

          if (modKeyFromNota){
            let r2 = moduleDateRangeMod.get(modKeyFromNota);
            if (!r2){
              r2 = { start: ymdDate, end: ymdDate };
              moduleDateRangeMod.set(modKeyFromNota, r2);
            } else {
              if (ymdDate < r2.start) r2.start = ymdDate;
              if (ymdDate > r2.end)   r2.end   = ymdDate;
            }

            const ti2 = ensureTimeInfo(moduleTimeInfoMod, modKeyFromNota);
            ti2.minStart = minTime(ti2.minStart, d);
            ti2.maxEnd   = maxTime(ti2.maxEnd, h);
            const spans2 = ti2.spansByDate.get(ymdDate) || [];
            spans2.push([d,h]);
            spans2.sort((A,B)=>A[0].localeCompare(B[0]));
            const merged2 = [];
            for (const s of spans2){
              if (!merged2.length){ merged2.push(s); continue; }
              const last = merged2[merged2.length-1];
              if (last[1] >= s[0]){
                if (s[1] > last[1]) last[1] = s[1];
              } else {
                merged2.push(s);
              }
            }
            ti2.spansByDate.set(ymdDate, merged2);
          }
        });
      });

      function buildHorarioSegments(det){
        const dates = Array.from(det.keys()).sort();
        if (!dates.length) return [];
        const segments=[];
        let cur = {from:dates[0], to:dates[0], desde:null, hasta:null};
        const updateTimes = (date, items)=>{
          (items||[]).forEach(it=>{
            const d=(it.desde||'').slice(0,5);
            const h=(it.hasta||'').slice(0,5);
            cur.desde = minTime(cur.desde,d);
            cur.hasta = maxTime(cur.hasta,h);
          });
        };
        updateTimes(dates[0], det.get(dates[0])||[]);
        for(let i=1;i<dates.length;i++){
          const prev=dates[i-1], cd=dates[i];
          if (dayDiff(prev,cd) > 7){
            segments.push(cur);
            cur = {from:cd,to:cd,desde:null,hasta:null};
          }else{
            cur.to = cd;
          }
          updateTimes(cd, det.get(cd)||[]);
        }
        segments.push(cur);
        return segments;
      }
	  
	        // Сливает подряд идущие сегменты с одинаковым horario (desde/hasta)
      function mergeHorarioSegmentsByTime(segs){
        if (!Array.isArray(segs) || !segs.length) return [];
        const out = [];
        let cur = {...segs[0]}; // копия первого

        for (let i = 1; i < segs.length; i++){
          const s = segs[i];
          const sameTime =
            (String(s.desde||'') === String(cur.desde||'')) &&
            (String(s.hasta||'') === String(cur.hasta||''));

          if (sameTime){
            // расширяем текущий сегмент по датам
            if (s.from < cur.from) cur.from = s.from;
            if (s.to   > cur.to)   cur.to   = s.to;
          } else {
            out.push(cur);
            cur = {...s}; // начинаем новый сегмент
          }
        }

        out.push(cur);
        return out;
      }

      const horarioSegs = buildHorarioSegments(det);
      const mergedSegs = mergeHorarioSegmentsByTime(horarioSegs);
      const months = monthsFromDet(det);
      const monthImgs = [];
      for (let i=0;i<months.length;i++){
        const ym = months[i];
        const detMonth = new Map();
        det.forEach((items, d)=>{ if (d.startsWith(ym)) detMonth.set(d, items); });
        const svg = buildMonthSVG(ym, detMonth, colorForKey);
        const png = await svgToRasterDataUrl(svg, {scale:0.6, mime:'image/png'});
        monthImgs.push({ ym, png });
        busy.pct(10 + Math.round((i+1)/Math.max(1,months.length)*40));
      }
      function renderMonthsTable(cells){
        let rows = '';
        for(let i = 0; i < cells.length; i += 2){
          const a = cells[i], b = cells[i+1];
          rows += `<tr>
            <td>${a ? `<img class="month" alt="${a.ym}" src="${a.png}">` : ''}</td>
            <td>${b ? `<img class="month" alt="${b.ym}" src="${b.png}">` : ''}</td>
          </tr>`;
        }
        return `<table class="months">${rows}</table>`;
      }
      const monthsTableHtml = renderMonthsTable(monthImgs);

      const mfPresent = new Set();
      det.forEach(items => {
        items.forEach(it => {
          const raw = (it.nota && it.nota.trim())
            ? it.nota.trim()
            : `${(it.desde||'').slice(0,5)}-${(it.hasta||'').slice(0,5)}`;
          const modKey = extractModuleKeyFromNota(raw);
          if (!modKey) return;
          const mfKey = mfByModuleKey.get(modKey) || modKey;
          mfPresent.add(mfKey);
        });
      });

      const orderedMF = groupedAll
        .filter(x=>x.type==='MF')
        .map(x=>x.key)
        .filter(k=>mfPresent.has(k));

      function legendHTML(){
        let html = '<div class="legend-mfs">';

				orderedMF.forEach(mfKey=>{
				  const mfMeta   = modsAll.find(m=>m.key===mfKey) || {label: mfKey, horas:0};
				  const color    = colorForKey(mfKey);
				  const rMF      = moduleDateRangeMF.get(mfKey);
				  const horasFromUFs = horasMFDesdeUF.get(mfKey) || 0;
				  const horasMFProp  = Number(mfMeta.horas || 0) || 0;
				  let horasMFShow    = 0;

				  if (horasFromUFs > 0) {
					horasMFShow = horasFromUFs;
				  } else if (horasMFProp > 0) {
					horasMFShow = horasMFProp;
				  } else {
					horasMFShow = horasMF.get(mfKey) || 0;
				  }

				  const mfLabelRaw = String(mfMeta.label || '').trim();
				  let mfTitleCore  = mfLabelRaw || mfKey;

				  // в конец названия добавляем "(XX horas)"
				  if (horasMFShow > 0) {
					mfTitleCore += ` (${horasMFShow} horas)`;
				  }

				  const rangoMF = rMF
					? `Del ${esDateDMY(rMF.start)} al ${esDateDMY(rMF.end)}`
					: '';

				// вместо headerLine
				const tituloMFHtml = esc(mfTitleCore);
				const rangoMFHtml  = rangoMF ? esc(rangoMF) : '';

				html += `
				  <table width="100%" cellspacing="0" cellpadding="6"
						 style="margin-bottom:6mm;border:1px solid #ccc;border-collapse:collapse;"
						 bgcolor="${color}">
					<tr bgcolor="${color}">
					  <td bgcolor="${color}" style="font-weight:bold;font-size:11pt;">
						<div>${tituloMFHtml}</div>
						${rangoMFHtml ? `<div style="font-weight:normal;">${rangoMFHtml}</div>` : ''}
					  </td>
					</tr>
					<tr bgcolor="${color}">
					  <td bgcolor="${color}" style="font-size:10pt;">
						<!-- тут остаётся блок с UFs как у тебя было -->
				`;

				  const ufs = modsAll.filter(m=>m.type==='UF' && m.group===mfKey);

				  ufs.forEach(uf=>{
					const rUF = moduleDateRangeMod.get(uf.key);
					const ti  = moduleTimeInfoMod.get(uf.key);

					const ufLabelRaw = String(uf.label || '').trim();
					const horasUF    = Number(uf.horas || 0) || 0;

					let ufTitleCore  = ufLabelRaw || uf.key;
					if (horasUF > 0) {
					  ufTitleCore += ` (${horasUF} horas)`;
					}

					html += `
			  <div style="margin:4px 0;font-size:10pt;">
				<b>${esc(ufTitleCore)}</b><br>
				${rUF ? `Del ${esDateDMY(rUF.start)} al ${esDateDMY(rUF.end)}` : ''}
			  </div>
		`;

					if (ti && ti.spansByDate && ti.spansByDate.size){
					  let fullDayMin = 0;
					  ti.spansByDate.forEach(spans=>{
						let mm = 0;
						(spans||[]).forEach(([a,b])=>{ mm += minutesBetween(a,b); });
						if (mm > fullDayMin) fullDayMin = mm;
					  });

					  const fechas = Array.from(ti.spansByDate.keys()).sort();
					  const first  = fechas[0];
					  const last   = fechas[fechas.length - 1];

					  function dayLine(d){
						const spans = ti.spansByDate.get(d)||[];
						if (!spans.length) return '';

						let mins = 0;
						spans.forEach(([a,b])=>{ mins += minutesBetween(a,b); });

						if (fullDayMin && mins === fullDayMin) return '';

						const horas = (mins/60).toFixed(1).replace('.',',');

						const intervalos = spans
						  .map(([a,b]) => `de ${a} a ${b}`)
						  .join(' y ');

						return `
				<div style="margin-left:12px;font-size:9.5pt;">
				  El ${esDateDMY(d)} el horario será de ${horas} horas (${intervalos})
				</div>`;
					  }

					  let extraHTML = '';
					  extraHTML += dayLine(first);
					  if (last !== first) extraHTML += dayLine(last);

					  if (extraHTML.trim()){
						html += extraHTML;
					  }
					}
				  });

				  html += `
			</td>
		  </tr>
		</table>
		`;
				});

				html += '</div>';
				return html;
			  }


      const totalHoras = Math.round(totalCourseMinutes(cursoMeta)/60)
        || Number(cursoMeta?.horas||cursoMeta?.total_horas||0) || 0;

      const entidad   = cursoMeta?.entidad || '';
      const tipoForm  = cursoMeta?.tipo_formacion || '';
      const anoAcad   = (()=>{
        if (!cursoStart) return '';
        const y1 = new Date(cursoStart+'T00:00:00').getFullYear();
        const y2 = cursoEnd
          ? new Date(cursoEnd+'T00:00:00').getFullYear()
          : y1;
        return `${y1}-${y2}`;
      })();
      const fechaIni  = esDateDMY(cursoStart);
      const fechaFin  = esDateDMY(cursoEnd);

      let horarioRows = '';
      mergedSegs.forEach((s,idx)=>{
        horarioRows += `
    <tr>
      <td class="hdr-label">${idx===0?'Horario:':''}</td>
      <td colspan="2" class="hdr-val">
        Del ${esDateDMY(s.from)} al ${esDateDMY(s.to)}
      </td>
      <td class="hdr-val hdr-time">${s.desde || ''}</td>
      <td class="hdr-val hdr-time">${s.hasta || ''}</td>
    </tr>`;
      });

      const cursoTxt = (cursosByCode.get(codigo)?.titulo || '—').toString().toUpperCase();

      const headerTableHtml = `
<table class="hdr-table">
  <tr>
    <td class="hdr-label">Nombre curso:</td>
    <td colspan="4" class="hdr-val">${esc(cursoTxt)}</td>
  </tr>
  <tr>
    <td class="hdr-label">Código curso:</td>
    <td class="hdr-val">${esc(codigo||'')}</td>
    <td class="hdr-label">Entidad:</td>
    <td colspan="2" class="hdr-val">${esc(entidad || ' ')}</td>
  </tr>
  <tr>
    <td class="hdr-label">Año académico:</td>
    <td class="hdr-val">${esc(anoAcad)}</td>
    <td class="hdr-label">Tipo formación:</td>
    <td colspan="2" class="hdr-val">${esc(tipoForm || ' ')}</td>
  </tr>
  <tr>
    <td class="hdr-label">Fechas impartición:</td>
    <td class="hdr-val">${esc(fechaIni)}</td>
    <td class="hdr-label center">a</td>
    <td colspan="2" class="hdr-val">${esc(fechaFin)}</td>
  </tr>
  ${horarioRows}
</table>`;

      busy.pct(70);

      const docTitle = `${String(codigo||'').toUpperCase()} — ${cursoTxt}`;
      const html = `
<!DOCTYPE html>
<html lang="es"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>${esc(docTitle)}</title>
  <style>
body{
  font-family:Arial,Segoe UI,system-ui;
  color:#142333;
  margin:0;
}
.doc{width:auto;max-width:none;margin:0}
.page{
  position:relative;
  page-break-after:always;
  margin:0;
  padding-top:70pt;
  padding-bottom:60pt;
}
.page-logo{
  position:absolute;
  display:block;
}
.page-logo.lanbide{
  top:18mm;
  left:18mm;
  width:80mm;
  height:auto;
}
.page-logo.eskadi{
  top:22mm;
  right:18mm;
  width:35mm;
  height:auto;
}
.page-logo.euro{
  bottom:18mm;
  right:22mm;
  width:28mm;
  height:auto;
}
@page WordSection1{
  size:A4;
  margin-top:20pt;
  margin-bottom:20pt;
  margin-left:10pt;
  margin-right:10pt;
  mso-page-orientation:portrait;
}
div.WordSection1{page:WordSection1;}
.hdr-table{width:100%;border-collapse:collapse;font-size:10pt;margin-bottom:8mm}
.hdr-table td{border:1px solid #d1d9e6;padding:3pt 5pt}
.hdr-label{background:#eef2f9;font-weight:700;white-space:nowrap}
.hdr-val{background:#ffffff}
.hdr-time{text-align:center}
.hdr-label.center{text-align:center}
table.months{width:100%;border-collapse:collapse;table-layout:fixed;margin:0}
table.months td{width:50%;padding:0;vertical-align:top}
img.month{width:100%;height:auto;display:block;margin:0}
.legend-page-title{font-size:13pt;font-weight:700;margin:0 0 2mm}
.legend-page-sub{font-size:11pt;font-weight:600;margin:0 0 6mm}
.legend-mfs{display:flex;flex-direction:column;gap:4mm}

/* Скрыть полностью ручной редактор из UI */
.mz-editor-card{
  display:none !important;
}

  </style>
</head>
<body>
  <div class="doc WordSection1">
    <div class="page">
      ${headerTableHtml}
      ${monthsTableHtml || '<p>No hay datos.</p>'}
    </div>

    <div class="page">
      <div class="legend-page-title">${esc(cursoTxt)}</div>
      <div class="legend-page-sub">(${totalHoras} horas)</div>
      ${legendHTML()}
    </div>
  </div>
</body>
</html>`;

      const headerJson = {
        nombreCurso: cursoTxt,
        codigo: codigo || '',
        entidad: entidad || '',
        anoAcademico: anoAcad || '',
        tipoFormacion: tipoForm || '',
        fechaIni: fechaIni,
        fechaFin: fechaFin,
        horarioSegs: mergedSegs.map(s => ({
          from: s.from,
          to:   s.to,
          desde: s.desde || '',
          hasta: s.hasta || ''
        }))
      };

      const calendarsJson = monthImgs.map(mi => ({
        ym: mi.ym,
        b64: mi.png.replace(/^data:image\/[^;]+;base64,/, '')
      }));

      const legendJson = orderedMF.map(mfKey => {
        const mfMeta = modsAll.find(m=>m.key===mfKey) || {label: mfKey, horas:0};
        const color  = colorForKey(mfKey);

        const rMF = moduleDateRangeMF.get(mfKey);
        const horasFromUFs = horasMFDesdeUF.get(mfKey) || 0;
        const horasMFProp  = Number(mfMeta.horas || 0) || 0;
        let horasMFShow    = 0;

        if (horasFromUFs > 0) {
          horasMFShow = horasFromUFs;
        } else if (horasMFProp > 0) {
          horasMFShow = horasMFProp;
        } else {
          horasMFShow = horasMF.get(mfKey) || 0;
        }

        const labelBase = (mfMeta.label || mfKey).trim();
        let tituloMF    = labelBase || mfKey;
        if (horasMFShow > 0) {
          tituloMF += ` (${horasMFShow} horas)`;
        }

        const rangoMF  = rMF ? `Del ${esDateDMY(rMF.start)} al ${esDateDMY(rMF.end)}` : '';
        const detallesMF = [];
        const ufs = modsAll
          .filter(m=>m.type==='UF' && m.group===mfKey)
          .map(uf => {
            const rUF = moduleDateRangeMod.get(uf.key);
            const ti  = moduleTimeInfoMod.get(uf.key);

            const labelUFBase = (uf.label || uf.key).trim();
            const horasUF     = Number(uf.horas || 0) || 0;
            let tituloUF      = labelUFBase || uf.key;
            if (horasUF > 0) {
              tituloUF += ` (${horasUF} horas)`;
            }

            const rangoUF  = rUF ? `Del ${esDateDMY(rUF.start)} al ${esDateDMY(rUF.end)}` : '';

            const detalles = [];
            if (ti && ti.spansByDate && ti.spansByDate.size) {
              const fechas = Array.from(ti.spansByDate.keys()).sort();
              let freq = new Map();
              let fullDayMin = 0;
              let maxCount = 0;

              fechas.forEach(d => {
                const spans = ti.spansByDate.get(d) || [];
                if (!spans.length) return;

                let mm = 0;
                spans.forEach(([a,b]) => { mm += minutesBetween(a,b); });

                const prev = freq.get(mm) || 0;
                const now  = prev + 1;
                freq.set(mm, now);

                if (now > maxCount) {
                  maxCount   = now;
                  fullDayMin = mm;
                }
              });

              if (!fullDayMin && freq.size) {
                fullDayMin = Array.from(freq.keys()).sort((a,b)=>b-a)[0];
              }

              fechas.forEach(d => {
                const spans = ti.spansByDate.get(d) || [];
                if (!spans.length) return;

                let mins = 0;
                spans.forEach(([a,b]) => { mins += minutesBetween(a,b); });
                if (fullDayMin && mins === fullDayMin) return;

                const horas = (mins/60).toFixed(1).replace('.',',');
                const intervalos = spans
                  .map(([a,b]) => `de ${a} a ${b}`)
                  .join(' y ');

                detalles.push(`El ${esDateDMY(d)} el horario será de ${horas} horas (${intervalos})`);
              });
            }

            return {
              key: uf.key,
              titulo: tituloUF,
              rango: rangoUF,
              detalles
            };
          });

        return {
          mfKey,
          color,
          titulo: tituloMF,
          rango: rangoMF,
          detallesMF,
          ufs
        };
      });
      const amb = (selTipo.value === 'practica') ? 'practica' : 'curso';
      let grp = '';
      if (amb === 'practica' && selAlumno && selAlumno.value) {
        grp = selAlumno.value.trim(); // тот же ID, что уходит в ?grupo=
      }

      const fname = `${codigo || 'curso'}_${amb}${grp ? ('_' + grp) : ''}_grafico.docx`;

const payload = {
  filename: fname,   // ADGG020854_curso.doc / .docx – как хочешь
  html,
  vacaciones: vacacionesSegs
};

const res = await fetch(`${API_BASE}/export-docx-graphic${qs()}`, {
  method: 'POST',
  headers: {
    ...auth(true),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});

if (!res.ok) {
  const t = await res.text().catch(() => '');
  throw new Error(t || `HTTP ${res.status}`);
}

const blob = await res.blob();
const url  = URL.createObjectURL(blob);

const a = document.createElement('a');
a.href = url;
a.download = fname;
document.body.appendChild(a);
a.click();
a.remove();
URL.revokeObjectURL(url);

      busy.off();

    }catch(e){
      console.error(e);
      busy.off();
      alert('Error al exportar DOCX: '+(e.message||'desconocido'));
    }
  }

})();