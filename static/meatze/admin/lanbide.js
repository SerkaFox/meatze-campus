(()=>{ 'use strict';

  if (window.__MZ_LANBIDE_V2__) return;
  window.__MZ_LANBIDE_V2__ = true;

const API_BASE = (window.MEATZE?.V5 || (location.origin + '/meatze/v5')).replace(/\/$/,'');
const API_A    = API_BASE + '/admin';


  const KEY = 'mz_admin';
  const tok = () => sessionStorage.getItem(KEY) || localStorage.getItem(KEY) || '';

  function auth(){
    const h = {};
    if (tok()) h['X-MZ-Admin'] = tok();
    return h;
  }

  const COLS = 6; // Persona, Eventos, Activo, Descargas, Físico, Última

  let initialized = false;
  function initOnce(){
    if (initialized) return;
    if (!tok()) return;

    const pane   = document.getElementById('ui-lanbide');
    const codigo = document.getElementById('lz-codigo');
    const load   = document.getElementById('lz-load');
    const tbody  = document.getElementById('lz-tbody');
    if (!pane || !codigo || !load || !tbody) return;

    initialized = true;
    boot();
  }

  function boot(){
    const el = {
      codigo: document.getElementById('lz-codigo'),
      from:   document.getElementById('lz-from'),
      to:     document.getElementById('lz-to'),
      role:   document.getElementById('lz-role'),
      load:   document.getElementById('lz-load'),
	  mode: document.getElementById('lz-mode'),
      export: document.getElementById('lz-export'),
      msg:    document.getElementById('lz-msg'),
      tbody:  document.getElementById('lz-tbody'),
      sumEvents: document.getElementById('lz-sum-events'),
      sumActive: document.getElementById('lz-sum-active'),
      sumRange:  document.getElementById('lz-sum-range'),
    };
	console.log('[LANBIDE] mode el:', el.mode, 'value=', el.mode?.value);


    let lastData = null;   // activity
    let lastMat  = null;   // material_report
    const KEY_LAST_COD = 'lz_last_codigo';

    const pad2 = n => String(n).padStart(2,'0');
    function fmtDate(d){
      if (!d) return '—';
      const dt = new Date(d);
      if (isNaN(dt.getTime())) return String(d);
      return `${dt.getFullYear()}-${pad2(dt.getMonth()+1)}-${pad2(dt.getDate())} ${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
    }
    function fmtHMS(sec){
      sec = parseInt(sec||0,10)||0;
      const h = Math.floor(sec/3600);
      const m = Math.floor((sec%3600)/60);
      const s = sec%60;
      if (h>0) return `${h}h ${m}m`;
      if (m>0) return `${m}m ${s}s`;
      return `${s}s`;
    }
    function esc(s){
      return String(s ?? '').replace(/[&<>"']/g, m => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
      }[m]));
    }
    function setMsg(text, isErr=false){
      if (!el.msg) return;
      el.msg.textContent = text || '';
      el.msg.style.color = isErr ? '#b91c1c' : '';
    }
    function setSummary(data){
      if (!data){
        el.sumEvents.textContent = '—';
        el.sumActive.textContent = '—';
        el.sumRange.textContent  = '—';
        return;
      }
      el.sumEvents.textContent = String(data.total_events ?? '—');
      el.sumActive.textContent = fmtHMS(data.total_active_sec ?? 0);
      const rf = data.range?.from || '—';
      const rt = data.range?.to   || '—';
      el.sumRange.textContent = `${rf} → ${rt}`;
    }

    async function loadCursos(){
      if (!el.codigo) return;
      if (el.codigo.dataset.loaded === '1') return;
      el.codigo.dataset.loaded = '1';

      const prev = el.codigo.value;
      el.codigo.disabled = true;

      try{
        const r = await fetch(`${API_A}/cursos?_=${Date.now()}`, { headers: auth(), cache:'no-store' });
        const j = await r.json().catch(()=>null);
        const items = (j && Array.isArray(j.items)) ? j.items : [];

        el.codigo.innerHTML = `<option value="">— Selecciona curso —</option>`;
        for (const c of items){
          const code = String(c.codigo || '').trim().toUpperCase();
          if (!code) continue;
          const title = String(c.titulo || '').trim();
          const opt = document.createElement('option');
          opt.value = code;
          opt.textContent = title ? `${code} · ${title}` : code;
          el.codigo.appendChild(opt);
        }

        const last = localStorage.getItem(KEY_LAST_COD) || '';
        if (prev) el.codigo.value = prev;
        else if (last) el.codigo.value = last;

      }catch(e){
        el.codigo.innerHTML = `<option value="">(Error cargando cursos)</option>`;
      }finally{
        el.codigo.disabled = false;
      }
    }

    function buildActivityUrl(){
      const codigo = (el.codigo.value||'').trim().toUpperCase();
      if (!codigo) return null;

      const params = new URLSearchParams();
      params.set('codigo', codigo);

      const role = (el.role?.value || '').trim();
      if (role) params.set('role', role);

      const dfrom = (el.from.value||'').trim();
      const dto   = (el.to.value||'').trim();
      if (dfrom) params.set('from', dfrom);
      if (dto)   params.set('to', dto);

      return `${API_A}/lanbide/activity?${params.toString()}`;
    }

async function fetchJsonSafe(url, init){
  const r = await fetch(url, init);
  let j = null;
  try { j = await r.json(); } catch(_) {}
  return { r, j };
}


async function loadMaterialReport(codigo){
  // новый admin endpoint (тот, что мы добавили на бэке)
  const url = `${API_A}/lanbide/material_status?codigo=${encodeURIComponent(codigo)}&_=${Date.now()}`;

  const r = await fetch(url, {
    headers: auth(),       // <-- X-MZ-Admin
    cache: 'no-store'
  });

  const j = await r.json().catch(()=>null);

  // ожидаем { ok:true, total_files, total_phys, items:{...} }
  if (!r.ok || !j || j.ok === false){
    throw new Error(j?.error || j?.detail || ('HTTP '+r.status));
  }

  return j;
}


function fmtHMSFull(sec){
  sec = parseInt(sec||0,10)||0;
  const h = Math.floor(sec/3600);
  const m = Math.floor((sec%3600)/60);
  const s = sec%60;
  // всегда читаемо
  if (h > 0) return `${h}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2,'0')}s`;
  return `${s}s`;
}

function csvCell(v){
  const s = String(v ?? '');
  // всегда в кавычках, чтобы не ломать запятые/переводы строк
  return `"${s.replaceAll('"','""')}"`;
}


    function findMatForUser(u){
      if (!lastMat || !lastMat.items) return null;

      // максимально “живучее” сопоставление ключей
      const candidates = [
        u.user_id, u.student_id, u.alumno_id, u.id
      ].filter(v => v !== undefined && v !== null && String(v).trim() !== '')
       .map(v => String(v));

      for (const k of candidates){
        if (Object.prototype.hasOwnProperty.call(lastMat.items, k)) return lastMat.items[k];
      }
      return null;
    }

    function rowHtml(u){
      const uid  = u.user_id ?? '';
      const name = (u.name || '').trim();
      const role = (u.role || '').trim();
      const who  = name ? name : `#${uid}`;

      const badge = role
        ? `<span style="margin-left:8px;font-size:11px;padding:2px 6px;border-radius:999px;border:1px solid #e5e7eb;background:#f8fafc;color:#334155">${esc(role)}</span>`
        : '';

      const events = parseInt(u.events||0,10)||0;
      const active = parseInt(u.active_sec||0,10)||0;
      const last   = u.last ? fmtDate(u.last) : '—';

const mi = findMatForUser(u);
const d  = mi ? (parseInt(mi.d||0,10)||0) : 0;
const r  = mi ? (parseInt(mi.r||0,10)||0) : 0;
const tf = Number(lastMat?.total_files || 0);
const tp = Number(lastMat?.total_phys  || 0);
const digital = statusText(d, tf, 'digital');
const fisico  = statusText(r, tp, 'physical');



      return `
        <tr style="border-bottom:1px solid #f1f5f9">
          <td style="padding:8px 10px">
            <b>${esc(who)}</b>${badge}
            <div class="mz-help" style="margin-top:2px">ID: ${esc(uid)}</div>
          </td>

          <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">${events}</td>
          <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">${fmtHMS(active)}</td>

          <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums"
              data-role="lz-progress" data-kind="dl" data-student-id="${esc(uid)}">${esc(digital)}</td>

          <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums"
              data-role="lz-progress" data-kind="rc" data-student-id="${esc(uid)}">${esc(fisico)}</td>

          <td style="padding:8px 10px">${esc(last)}</td>
        </tr>
      `;
    }

function render(data){
  const mode = (el.mode?.value || 'summary');

  el.export.disabled = true;

  if (!data){
    el.tbody.innerHTML = `<tr><td colspan="${COLS}" style="padding:10px" class="mz-help">No hay datos.</td></tr>`;
    setSummary(null);
    return;
  }

  // SUMMARY
  if (mode === 'summary'){
    el.export.disabled = !Array.isArray(data.users) || !data.users.length;
    setSummary(data);

    const list = Array.isArray(data.users) ? data.users : [];
    if (!list.length){
      el.tbody.innerHTML = `<tr><td colspan="${COLS}" style="padding:10px" class="mz-help">Sin actividad en este rango.</td></tr>`;
      return;
    }
    el.tbody.innerHTML = list.map(rowHtml).join('');
    return;
  }

  // DAILY
  if (mode === 'daily'){
    // summary-block можно переиспользовать, но логичнее показать totals по rows
    const rows = Array.isArray(data.rows) ? data.rows : [];
    // посчитаем totals на фронте:
    const totalEvents = rows.reduce((a,x)=>a+(parseInt(x.events||0,10)||0),0);
    const totalActive = rows.reduce((a,x)=>a+(parseInt(x.active_sec||0,10)||0),0);

    setSummary({
      total_events: totalEvents,
      total_active_sec: totalActive,
      range: data.range || {}
    });

    el.export.disabled = !rows.length;

    if (!rows.length){
      el.tbody.innerHTML = `<tr><td colspan="${COLS}" style="padding:10px" class="mz-help">Sin actividad en este rango.</td></tr>`;
      return;
    }


    // другой формат строки (day + first/last)
    el.tbody.innerHTML = rows.map(dailyRowHtml).join('');
    return;
  }
}

function dailyRowHtml(r){
  const persona = (r.name || '').trim() || `#${r.user_id ?? ''}`;
  const role = (r.role || '').trim();
  const badge = role
    ? `<span style="margin-left:8px;font-size:11px;padding:2px 6px;border-radius:999px;border:1px solid #e5e7eb;background:#f8fafc;color:#334155">${esc(role)}</span>`
    : '';

  const day = r.day || '—';
  const events = parseInt(r.events||0,10)||0;
  const active = parseInt(r.active_sec||0,10)||0;
  const first = r.first ? fmtDate(r.first) : '—';
  const last  = r.last  ? fmtDate(r.last)  : '—';

  return `
    <tr style="border-bottom:1px solid #f1f5f9">
      <td style="padding:8px 10px">
        <b>${esc(persona)}</b>${badge}
        <div class="mz-help" style="margin-top:2px">${esc(day)} · ${esc(first)} → ${esc(last)}</div>
      </td>
      <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">${events}</td>
      <td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">${fmtHMS(active)}</td>
      <td style="padding:8px 10px;text-align:right" class="mz-help">—</td>
      <td style="padding:8px 10px;text-align:right" class="mz-help">—</td>
      <td style="padding:8px 10px">${esc(last)}</td>
    </tr>
  `;
}



async function load(){
  const codigo = (el.codigo.value||'').trim().toUpperCase();
  if (!codigo){ setMsg('Selecciona curso.', true); return; }

  const mode = (el.mode?.value || 'summary');
  const url = (mode === 'daily') ? buildDailyUrl() : buildActivityUrl();
  if (!url){ setMsg('Faltan datos.', true); return; }

  setMsg('Cargando…');
  el.load.disabled = true;

  try{
    const { r, j } = await fetchJsonSafe(url, { headers: auth(), cache:'no-store' });

    if (!r.ok || !j || j.ok === false){
      setMsg((j && (j.error || j.detail)) ? String(j.error||j.detail) : ('Error HTTP '+r.status), true);
      lastData = null;
      render(null);
      return;
    }
	if (mode === 'summary'){
	  try{
		lastMat = await loadMaterialReport(codigo);
	  }catch(_){
		lastMat = null;
	  }
	}

    // важно: daily отдаёт rows, summary отдаёт users — сохраним как есть
    lastData = j;
    setMsg('OK');

    // render должен понимать оба режима (ниже)
    render(j);

  }catch(e){
    setMsg('Error de red', true);
    lastData = null;
    render(null);
  }finally{
    el.load.disabled = false;
  }
}

function statusText(done, total, kind){
  // kind: 'digital' | 'physical'
  done = parseInt(done||0,10)||0;
  total = parseInt(total||0,10)||0;

  const okTxt  = (kind==='physical') ? 'Físico: recibido completo' : 'Digital: recibido completo';
  const noTxt  = (kind==='physical') ? 'Físico: no recibido'       : 'Digital: no recibido';
  const partTxt= (kind==='physical') ? 'Físico: incompleto'        : 'Digital: incompleto';

  if (total <= 0){
    // если нет “плана” по количеству — показываем просто факт
    return done > 0 ? ((kind==='physical') ? `Físico: ${done}` : `Digital: ${done}`) : noTxt;
  }

  if (done <= 0) return noTxt;
  if (done >= total) return okTxt;
  return `${partTxt} (${done}/${total})`; // можно убрать (done/total) если не хочешь вообще цифры
}

// если хочешь вообще без цифр — используй это вместо statusText:
function statusTextNoNumbers(done, total, kind){
  done = parseInt(done||0,10)||0;
  total = parseInt(total||0,10)||0;

  const okTxt  = (kind==='physical') ? 'Físico: recibido completo' : 'Digital: recibido completo';
  const noTxt  = (kind==='physical') ? 'Físico: no recibido'       : 'Digital: no recibido';
  const partTxt= (kind==='physical') ? 'Físico: incompleto'        : 'Digital: incompleto';

  if (total <= 0) return done > 0 ? partTxt : noTxt;
  if (done <= 0) return noTxt;
  if (done >= total) return okTxt;
  return partTxt;
}

function hms(sec){
  sec = parseInt(sec||0,10)||0;
  const h = Math.floor(sec/3600);
  const m = Math.floor((sec%3600)/60);
  const s = sec%60;
  const pad = n => String(n).padStart(2,'0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function csvCell(v){
  const s = String(v ?? '');
  return `"${s.replaceAll('"','""')}"`;
}

function downloadCsv(){
  if (!lastData) return;

  const codigo = (lastData.codigo||'').trim() || (el.codigo.value||'').trim() || 'curso';
  const rf = lastData.range?.from || '';
  const rt = lastData.range?.to || '';

  const mode = (el.mode?.value || 'summary');

  // --- SUMMARY CSV ---
  if (mode === 'summary'){
    if (!Array.isArray(lastData.users) || !lastData.users.length) return;

    const header = ['curso','from','to','persona','rol','eventos','tiempo_activo','digital','fisico','ultima'];
    const lines = [header.join(',')];

    for (const u of lastData.users){
      const persona = (u.name || '').trim() || `#${u.user_id ?? ''}`;
      const rol = (u.role || '').trim();
      const eventos = parseInt(u.events||0,10)||0;
      const activo = hms(u.active_sec||0);

const mi = findMatForUser(u);
const d  = mi ? (parseInt(mi.d||0,10)||0) : 0;
const r  = mi ? (parseInt(mi.r||0,10)||0) : 0;
const tf = Number(lastMat?.total_files || 0);
const tp = Number(lastMat?.total_phys  || 0);
const digital = statusText(d, tf, 'digital');
const fisico  = statusText(r, tp, 'physical');


      const ultima = u.last || '';

      const row = [
        codigo, rf, rt,
        persona, rol,
        eventos,
        activo,
        digital,
        fisico,
        ultima
      ].map(csvCell);

      lines.push(row.join(','));
    }

    const blob = new Blob([lines.join('\n')], {type:'text/csv;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `lanbide_${codigo}_resumen_${rf||'from'}_${rt||'to'}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 0);
    return;
  }

  // --- DAILY CSV ---
  if (mode === 'daily'){
    if (!Array.isArray(lastData.rows) || !lastData.rows.length) return;

    const header = ['curso','from','to','dia','persona','rol','eventos','tiempo_activo','primera','ultima'];
    const lines = [header.join(',')];

    for (const r of lastData.rows){
      const dia = r.day || '';
      const persona = (r.name || '').trim() || `#${r.user_id ?? ''}`;
      const rol = (r.role || '').trim();
      const eventos = parseInt(r.events||0,10)||0;
      const activo = hms(r.active_sec||0);
      const primera = r.first || '';
      const ultima  = r.last || '';

      const row = [
        codigo, rf, rt,
        dia, persona, rol,
        eventos,
        activo,
        primera,
        ultima
      ].map(csvCell);

      lines.push(row.join(','));
    }

    const blob = new Blob([lines.join('\n')], {type:'text/csv;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `lanbide_${codigo}_daily_${rf||'from'}_${rt||'to'}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }
}

function buildDailyUrl(){
  const codigo = (el.codigo.value||'').trim().toUpperCase();
  if (!codigo) return null;

  const params = new URLSearchParams();
  params.set('codigo', codigo);

  const role = (el.role?.value || '').trim();
  if (role) params.set('role', role);

  const dfrom = (el.from.value||'').trim();
  const dto   = (el.to.value||'').trim();
  if (dfrom) params.set('from', dfrom);
  if (dto)   params.set('to', dto);

  return `${API_A}/lanbide/daily?${params.toString()}`;
}


    // listeners
    el.load.addEventListener('click', load);

    el.codigo.addEventListener('change', ()=>{
      const v = (el.codigo.value||'').trim();
      localStorage.setItem(KEY_LAST_COD, v);
      if (v) load();
    });

	el.mode?.addEventListener('change', ()=>{
		  console.log('[LANBIDE] mode change ->', el.mode?.value);
	  const v = (el.codigo.value||'').trim();
	  if (v) load();
	});

    el.role?.addEventListener('change', ()=>{
      const v = (el.codigo.value||'').trim();
      if (v) load();
    });

    el.export.addEventListener('click', downloadCsv);

    loadCursos().then(()=>{
      const v = (el.codigo.value||'').trim();
      if (v) load();
    });
  }

  // init triggers
  if (tok()) initOnce();
  document.addEventListener('mz:admin-auth', (e)=>{ if (e?.detail?.ok) initOnce(); });
  document.getElementById('ui-lanbide')?.addEventListener('mz:pane:show', ()=> initOnce());

})();
