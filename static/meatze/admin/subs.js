(() => {
  'use strict';

  const $ = (s, root = document) => root.querySelector(s);
  const WA_PAGE_SIZE = 10;
  let waPage = 1;
  let previewObjectUrl = null;
  let waSelectedManual = new Set(); // номера, выбранные для рассылки

  let cancelBroadcast = false;
  let subsCache = null;

  // API helpers
  // В Django wpApiSettings нет, так что достаточно корня + /meatze/v5
  const API_BASE = '/meatze/v5';
  // Новый namespace, чтобы не мешать старым /news/*
  const API_N = API_BASE + '/notify';
  const tok = () => sessionStorage.getItem('mz_admin') || '';
const qs = (bust=false) => (bust ? `?_=${Date.now()}` : '');

  const auth= (isPost=false)=> {
    const h = {};
    if (tok()) h['X-MZ-Admin'] = tok();
    if (isPost) h['Content-Type'] = 'application/json';
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
  function sleep(ms){ return new Promise(res => setTimeout(res, ms)); }

  // ===== выбор получателей =====
  function renderSelectedRecipients(){
    const box = $('#mzs-picked-list');
    if (!box) return;

    box.innerHTML = '';

    if (!waSelectedManual.size){
      box.innerHTML = '<div class="mz-help">Todavía no hay contactos seleccionados.</div>';
      return;
    }

    const waMap = (subsCache && subsCache.wa) || {};
    const items = Array.from(waSelectedManual).map(num => {
      const p = waMap[num] || {};
      return {
        num,
        name: (p.name || 'Contacto').trim(),
        loc:  (p.loc || '').trim()
      };
    });

    items.sort((a,b) => {
      const na = a.name.toLowerCase();
      const nb = b.name.toLowerCase();
      if (na !== nb) return na.localeCompare(nb, 'es', {sensitivity:'base'});
      return a.num.localeCompare(b.num);
    });

    for (const it of items){
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'center';
      row.style.justifyContent = 'space-between';
      row.style.padding = '4px 4px';
      row.style.borderBottom = '1px solid #edf2f7';

      const label = document.createElement('div');
      label.innerHTML = `
        <strong>${it.name}</strong><br>
        <span class="mz-help">${it.num}${it.loc ? ' · ' + it.loc : ''}</span>
      `;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mz-btn link sm';
      btn.style.padding = '2px 6px';
      btn.textContent = '✕';
      btn.addEventListener('click', () => {
        waSelectedManual.delete(it.num);
        const sel = $('#mzs-sel-wa');
        if (sel){
          Array.from(sel.options).forEach(o => {
            if (o.value === it.num) o.selected = false;
          });
        }
        renderSelectedRecipients();
        updatePreview();
      });

      row.appendChild(label);
      row.appendChild(btn);
      box.appendChild(row);
    }
  }

  function addWaSelected(num){
    if (!num) return;
    waSelectedManual.add(String(num));
    renderSelectedRecipients();
    updatePreview();
  }

  function syncPicked(){
    const v = (document.querySelector('input[name="mzs-mode"]:checked')?.value) || 'all';
    $('#mzs-picked').style.display = (v === 'selected') ? 'grid' : 'none';
    updatePreview();
  }

  // ===== прогресс-оверлей =====
  function showProgress(main, sub=''){
    cancelBroadcast = false;
    const box = $('#mzs-progress');
    if (!box) return;
    $('#mzs-progress-text').textContent = main || 'Procesando…';
    $('#mzs-progress-sub').textContent  = sub || '';
    box.style.display = 'flex';
  }
  function updateProgress(main, sub){
    if ($('#mzs-progress-text')) {
      $('#mzs-progress-text').textContent = main;
    }
    if ($('#mzs-progress-sub') && typeof sub !== 'undefined') {
      $('#mzs-progress-sub').textContent = sub;
    }
  }
  function hideProgress(){
    const box = $('#mzs-progress');
    if (box) box.style.display = 'none';
  }

  // ===== превью WA =====
  function getPreviewName(){
    const def = 'alumno/a';
    if (!subsCache || !subsCache.wa) return def;

    const locFilter   = $('#mzs-filter-loc') ? $('#mzs-filter-loc').value : '';
    const searchInput = $('#mzs-wa-search');
    const q           = searchInput ? (searchInput.value || '').trim().toLowerCase() : '';

    const waObj = subsCache.wa || {};
    const all   = Object.entries(waObj);

    let filtered = locFilter
      ? all.filter(([num, p]) => (p.loc || '') === locFilter)
      : all;

    const mode = document.querySelector('input[name="mzs-mode"]:checked')?.value || 'all';

    if (mode === 'selected' && waSelectedManual.size) {
      const firstNum = Array.from(waSelectedManual)[0];
      const p = waObj[firstNum] || {};
      const nm = (p.name || '').trim();
      return nm || def;
    }

    if (!filtered.length) return def;

    const first = filtered[0][1] || {};
    const nm = (first.name || '').trim();
    return nm || def;
  }

  function getCurrentFile(){
    const fi = $('#mzs-wa-file');
    return (fi && fi.files && fi.files[0]) ? fi.files[0] : null;
  }

  function applyWaSearchFilter(){
    const search = $('#mzs-wa-search');
    const sel    = $('#mzs-sel-wa');
    if (!search || !sel) return;

    const q    = search.value.trim().toLowerCase();
    const opts = Array.from(sel.options || []);

    opts.forEach(opt => {
      const txt  = (opt.textContent || '').toLowerCase();
      const hide = q && !txt.includes(q);
      opt.hidden = hide;
    });
  }

  function updatePreview(){
    const textEl  = $('#mzs-preview-text');
    const mediaEl = $('#mzs-preview-media');
    if (!textEl || !mediaEl) return;

    mediaEl.innerHTML = '';
    if (previewObjectUrl) {
      try { URL.revokeObjectURL(previewObjectUrl); } catch(_){}
      previewObjectUrl = null;
    }

    const name     = getPreviewName();
    const textRaw  = $('#mzs-text') ? ($('#mzs-text').value || '') : '';
    const textTrim = textRaw.trim();
    const file     = getCurrentFile();

    const bodyPart = textTrim || '…';
    const previewText =
      `Hola ${name},\n\n` +
      `${bodyPart}\n\n` +
      `“Gracias por formar parte de MEATZE.”\n` +
      `Responde aquí y te contactaremos en breve.`;

    textEl.textContent = previewText;

    if (!file) return;

    const fname = file.name.toLowerCase();
    const isImg = /\.(jpe?g|png)$/.test(fname);
    const isPdf = /\.pdf$/.test(fname);

    if (!isImg && !isPdf) {
      mediaEl.innerHTML = `<div style="font-size:12px;color:#6b7280">
        Archivo adjunto: ${file.name}
      </div>`;
      return;
    }

    const url = URL.createObjectURL(file);
    previewObjectUrl = url;

    if (isImg) {
      const img = document.createElement('img');
      img.src = url;
      img.alt = file.name;
      img.style.maxWidth = '100%';
      img.style.borderRadius = '10px';
      img.style.display = 'block';
      mediaEl.appendChild(img);
    } else if (isPdf) {
      const wrap = document.createElement('div');
      wrap.innerHTML = `
        <div style="font-size:12px;color:#6b7280;margin-bottom:4px">
          Documento PDF: ${file.name}
        </div>
        <embed src="${url}" type="application/pdf"
               style="width:100%;height:200px;border:1px solid #e5e7eb;border-radius:8px" />
      `;
      mediaEl.appendChild(wrap);
    }
  }

  // ===== импорт WA =====
  async function handleWaImport(){
    const fileInput = $('#mzs-wa-import-file');
    const locSel    = $('#mzs-wa-import-loc');
    const msg       = $('#mzs-wa-import-msg');

    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
      alert('Selecciona un fichero primero');
      return;
    }

    msg.textContent = '';
    msg.style.color = '';

    const loc  = locSel ? (locSel.value || '') : '';
    const file = fileInput.files[0];

    const fd = new FormData();
    fd.append('file', file);
    fd.append('loc', loc);

    try{
      const r   = await fetch(`${API_N}/wa-import${qs()}`, {
        method: 'POST',
        headers: { 'X-MZ-Admin': tok() || '' },
        body: fd
      });
      const txt = await r.text();
      let j = {};
      try { j = txt ? JSON.parse(txt) : {}; } catch(e) {
        throw new Error(`HTTP ${r.status} — ${txt.slice(0,160)}`);
      }
      if (!r.ok || !j.ok) {
        throw new Error(j.message || 'Error en importación');
      }

      msg.style.color = '#0b6d22';
      const ins = j.inserted || 0;
      const upd = j.updated  || 0;
      const sk  = j.skipped  || 0;
      msg.textContent = `Importado: nuevos ${ins}, actualizados ${upd}, omitidos ${sk}`;
      loadSubs();
    }catch(e){
      msg.style.color = '#b90e2e';
      msg.textContent = e.message || 'Error en importación';
    }
  }

  // ===== загрузка подписчиков =====
  async function loadSubs(){
    $('#mzs-wa-body').innerHTML = '<tr><td colspan="5">Cargando…</td></tr>';
    try{
      const j = await apiJSON(`${API_N}/subscribers${qs(true)}`, {headers:auth()});
      subsCache = j;
      drawSubs(j);
      updatePreview();
    }catch(e){
      $('#mzs-wa-body').innerHTML = '<tr><td colspan="5">Error</td></tr>';
      updatePreview();
    }
  }

  function drawSubs(j){
    const selW      = $('#mzs-sel-wa');
    const wb        = $('#mzs-wa-body');
    const locFilter = $('#mzs-filter-loc') ? $('#mzs-filter-loc').value : '';
    const searchInput = $('#mzs-wa-search');
    const q = searchInput ? (searchInput.value || '').trim().toLowerCase() : '';

    selW.innerHTML = '';
    wb.innerHTML   = '';

    const wa  = j.wa || {};
    const all = Object.entries(wa);

    let filtered = locFilter
      ? all.filter(([num, p]) => (p.loc || '') === locFilter)
      : all;

    if (q) {
      filtered = filtered.filter(([num, p]) => {
        const name   = (p.name || '').toLowerCase();
        const numStr = String(num || '').toLowerCase();
        return name.includes(q) || numStr.includes(q);
      });
    }

    filtered.sort((a,b) => {
      const na = (a[1].name || '').toLowerCase();
      const nb = (b[1].name || '').toLowerCase();
      if (na && nb && na !== nb) return na.localeCompare(nb, 'es', {sensitivity:'base'});
      return String(a[0]).localeCompare(String(b[0]));
    });

    if (q) {
      filtered = filtered.filter(([num, p]) => {
        const name   = (p.name || '').toLowerCase();
        const numStr = String(num || '').toLowerCase();
        return name.includes(q) || numStr.includes(q);
      });
    }

    const total = filtered.length;
    if (!total) {
      wb.innerHTML = '<tr><td colspan="5">Vacío</td></tr>';
      $('#mzs-counts').textContent = 'WA: 0 (total 0)';
      const info = $('#mzs-wa-page-info');
      if (info) info.textContent = '';
      const prev = $('#mzs-wa-prev'), next = $('#mzs-wa-next');
      if (prev && next) { prev.disabled = true; next.disabled = true; }
      return;
    }

    for (const [num, p] of filtered) {
      const label = (p.name ? p.name + ' · ' : '') + num;
      const opt = document.createElement('option');
      opt.value = num;
      opt.textContent = label;
      if (waSelectedManual.has(String(num))) {
        opt.selected = true;
      }
      selW.appendChild(opt);
    }

    const pages = Math.max(1, Math.ceil(total / WA_PAGE_SIZE));
    if (waPage > pages) waPage = pages;
    if (waPage < 1) waPage = 1;
    const start      = (waPage - 1) * WA_PAGE_SIZE;
    const pageItems  = filtered.slice(start, start + WA_PAGE_SIZE);

    if (!pageItems.length) {
      wb.innerHTML = '<tr><td colspan="5">Vacío</td></tr>';
    }

    for (const [num, p] of pageItems) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${num}</code></td>
        <td>${p.name ? p.name : '—'}</td>
        <td>${p.loc  ? p.loc  : '—'}</td>
        <td>${p.active ? '<span style="color:#0b6d22">activo</span>'
                       : '<span style="color:#8a1233">pausa</span>'}</td>
        <td style="white-space:nowrap">
          <button class="mz-btn link"   data-edit>Editar</button>
          <button class="mz-btn link"   data-toggle>Toggle</button>
          <button class="mz-btn danger" data-del>Eliminar</button>
        </td>`;

      tr.querySelector('[data-edit]').onclick = ()=> {
        $('#mzs-wa-edit-num').value      = num;
        $('#mzs-wa-edit-name').value     = p.name || '';
        $('#mzs-wa-edit-loc').value      = p.loc || '';
        $('#mzs-wa-edit-active').checked = !!p.active;
      };

      tr.querySelector('[data-toggle]').onclick = async () => {
        await apiJSON(`${API_N}/wa-toggle${qs()}`, {
          method:'POST', headers:auth(true),
          body:JSON.stringify({wa:num})
        });
        loadSubs();
      };

      tr.querySelector('[data-del]').onclick = async () => {
        if (!confirm('¿Eliminar WA?')) return;
        await apiJSON(`${API_N}/wa-delete${qs()}`, {
          method:'POST', headers:auth(true),
          body:JSON.stringify({wa:num})
        });
        loadSubs();
      };

      wb.appendChild(tr);
    }

    const counts = $('#mzs-counts');
    if (counts) {
      counts.textContent = `WA: ${pageItems.length} (página ${waPage}/${pages}, total ${total})`;
    }
    const pageInfo = $('#mzs-wa-page-info');
    if (pageInfo) {
      pageInfo.textContent = (pages > 1)
        ? `Página ${waPage} de ${pages}`
        : '';
    }
    const prev = $('#mzs-wa-prev'), next = $('#mzs-wa-next');
    if (prev && next) {
      prev.disabled = (waPage <= 1);
      next.disabled = (waPage >= pages);
    }

    renderSelectedRecipients();
  }

  function getWaTargets(mode, waLoc){
    if (!subsCache || !subsCache.wa) return [];

    const waMap = subsCache.wa || {};
    const all   = Object.entries(waMap);

    let filtered = all.filter(([num, p]) => {
      if (!p) return false;
      if (!p.active) return false;
      if (waLoc && p.loc !== waLoc) return false;
      return true;
    });

    if (mode === 'selected') {
      if (!waSelectedManual.size) return [];
      filtered = filtered.filter(([num]) => waSelectedManual.has(String(num)));
    }

    return filtered.map(([num, p]) => ({
      wa: String(num),
      name: (p.name || '').trim() || 'alumno/a',
    }));
  }

  // ===== отправка рассылки =====
  async function sendNow(){
    const note = $('#mzs-msg');
    note.textContent = '';
    note.style.color = '';

    const mode    = document.querySelector('input[name="mzs-mode"]:checked')?.value || 'all';
    const waLoc   = $('#mzs-filter-loc') ? $('#mzs-filter-loc').value : '';
    const textRaw = $('#mzs-text').value || '';
    const textTrim = textRaw.trim();
    const file     = getCurrentFile();

    let waTpl      = 'personal_txt';
    let needUpload = false;

    if (file) {
      const name  = file.name.toLowerCase();
      const isImg = /\.(jpe?g|png)$/.test(name);
      const isPdf = /\.pdf$/.test(name);

      if (!isImg && !isPdf) {
        note.style.color   = '#b90e2e';
        note.textContent   = 'Solo se admiten imágenes JPG/PNG o PDF.';
        return;
      }
      if (!textTrim) {
        note.style.color   = '#b90e2e';
        note.textContent   = 'Escribe el texto del mensaje para acompañar el archivo.';
        return;
      }

      if (isImg) waTpl = 'personal_photo';
      if (isPdf) waTpl = 'personal_doc';
      needUpload = true;
    } else {
      if (!textTrim) {
        note.style.color   = '#b90e2e';
        note.textContent   = 'Escribe el texto del mensaje.';
        return;
      }
      waTpl = 'personal_txt';
    }

    const subjEl = $('#mzs-subj');
    const subj   = subjEl ? subjEl.value.trim() : '';

    const baseBody = {
      channels: ['wa'],
      mode,
      subject: subj,
      text:    textRaw,

      test_chat_id: '',
      test_wa:      '',

      sel_tg:    [],
      sel_email: [],
      sel_wa:    [],

      wa_tpl: waTpl,
      wa_media_url: '',
      wa_loc: waLoc
    };

    if (needUpload && file) {
      const fd = new FormData();
      fd.append('file', file);
      try{
        const r   = await fetch(`${API_N}/upload-wa${qs()}`, {
          method:'POST',
          headers: { 'X-MZ-Admin': tok() || '' },
          body: fd
        });
        const txt = await r.text();
        let j = null;
        try{ j = txt ? JSON.parse(txt) : {}; }catch(_){ throw new Error(`Upload HTTP ${r.status} — ${txt.slice(0,160)}`); }
        if (!r.ok || !j.ok) throw new Error(j.message || 'Error subiendo fichero');
        baseBody.wa_media_url  = j.url || '';
        baseBody.wa_media_name = j.filename || '';
      }catch(e){
        note.style.color   = '#b90e2e';
        note.textContent   = e.message || 'Error al subir fichero WA';
        return;
      }
    }

    const targets = getWaTargets(mode, waLoc);

    if (!targets.length){
      note.style.color   = '#b90e2e';
      note.textContent   = 'No hay destinatarios.';
      return;
    }

    showProgress(`Preparando envío… (${targets.length} contactos)`, '');
    cancelBroadcast = false;

    let ok = 0, fail = 0;

    try {
      for (let i = 0; i < targets.length; i++) {
        const { wa, name } = targets[i];

        if (cancelBroadcast) {
          updateProgress(
            'Envío cancelado',
            `Se enviaron ${ok} de ${targets.length} contactos.`
          );
          break;
        }

        updateProgress(
          `Enviando a ${name} (${wa}) (${i+1}/${targets.length})…`,
          'Esto puede tardar unos minutos, por favor, espera.'
        );

        try {
          await apiJSON(`${API_N}/broadcast${qs()}`, {
            method:'POST',
            headers:auth(true),
            body:JSON.stringify({
              ...baseBody,
              mode: 'selected',
              sel_wa: [wa],
            })
          });

          ok++;
          updateProgress(
            `✔ Enviado a ${name} (${wa}) (${i+1}/${targets.length})`,
            ''
          );
        } catch(e){
          fail++;
          updateProgress(
            `❌ Error con ${name} (${wa}) (${i+1}/${targets.length})`,
            e.message || 'Error desconocido'
          );
        }

        await sleep(500);
      }

    } finally {
      hideProgress();

      note.style.color = (fail === 0 && !cancelBroadcast) ? '#0b6d22' : '#b90e2e';

      if (cancelBroadcast) {
        note.textContent = `Cancelado · enviados ${ok} de ${targets.length} · fallos ${fail}`;
      } else {
        note.textContent = `Completado · OK ${ok} · Fallos ${fail}`;
      }
    }
  }

  // ===== init (только для ui-subs) =====
  let inited = false;
  function initOnce(){
    if (inited || !tok()) return;
    inited = true;
    boot();
  }

  function boot(){
    document.querySelectorAll('input[name="mzs-mode"]').forEach(r =>
      r.addEventListener('change', syncPicked)
    );
    syncPicked();

    const locSel = $('#mzs-filter-loc');
    if (locSel) {
      locSel.addEventListener('change', () => {
        waPage = 1;
        if (subsCache) drawSubs(subsCache);
        updatePreview();
      });
    }

    const selWa = $('#mzs-sel-wa');
    if (selWa) {
      selWa.addEventListener('change', () => {
        const opts = Array.from(selWa.selectedOptions || []);
        opts.forEach(o => addWaSelected(o.value));
      });
    }

    const cancelBtn = $('#mzs-progress-cancel');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        cancelBroadcast = true;
        updateProgress('Cancelando envíos…', 'Se detendrá tras el mensaje actual.');
      });
    }

    const txt = $('#mzs-text');
    if (txt) {
      txt.addEventListener('input', updatePreview);
    }

    const searchInput = $('#mzs-wa-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        const q = searchInput.value || '';

        if (q.length >= 1) {
          const selRadio = document.querySelector('input[name="mzs-mode"][value="selected"]');
          if (selRadio && !selRadio.checked) {
            selRadio.checked = true;
            syncPicked();
          }
        }

        applyWaSearchFilter();

        if (subsCache) {
          waPage = 1;
          drawSubs(subsCache);
        }
      });
    }

    const fileInput    = $('#mzs-wa-file');
    const fileNameSpan = $('#mzs-wa-file-name');
    const fileClearBtn = $('#mzs-wa-file-clear');
    if (fileInput) {
      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files[0]) {
          fileNameSpan.textContent = fileInput.files[0].name;
          if (fileClearBtn) fileClearBtn.style.display = 'inline-flex';
        } else {
          fileNameSpan.textContent = '';
          if (fileClearBtn) fileClearBtn.style.display = 'none';
        }
        updatePreview();
      });
    }
    if (fileClearBtn && fileInput) {
      fileClearBtn.addEventListener('click', () => {
        fileInput.value = '';
        fileNameSpan.textContent = '';
        fileClearBtn.style.display = 'none';
        updatePreview();
      });
    }

    const btnPrev = $('#mzs-wa-prev');
    const btnNext = $('#mzs-wa-next');
    if (btnPrev && btnNext) {
      btnPrev.addEventListener('click', ()=> {
        if (waPage > 1) {
          waPage--;
          if (subsCache) drawSubs(subsCache);
        }
      });
      btnNext.addEventListener('click', ()=> {
        waPage++;
        if (subsCache) drawSubs(subsCache);
      });
    }

    const btnSaveWa = $('#mzs-wa-edit-save');
    if (btnSaveWa) {
      btnSaveWa.addEventListener('click', async ()=> {
        const num = $('#mzs-wa-edit-num').value.trim();
        if (!num) { alert('Número obligatorio'); return; }

        const body = {
          wa:     num,
          name:   $('#mzs-wa-edit-name').value.trim(),
          loc:    $('#mzs-wa-edit-loc').value,
          active: $('#mzs-wa-edit-active').checked ? 1 : 0,
        };

        try{
          await apiJSON(`${API_N}/wa-upsert${qs()}`, {
            method:'POST',
            headers:auth(true),
            body:JSON.stringify(body)
          });
          loadSubs();
        }catch(e){
          alert(e.message || 'Error guardando WA');
        }
      });
    }

    const btnImport = $('#mzs-wa-import-run');
    if (btnImport) {
      btnImport.addEventListener('click', handleWaImport);
    }

    const btnSend = $('#mzs-send');
    if (btnSend) {
      btnSend.addEventListener('click', sendNow);
    }

    const btnRefresh = $('#mzs-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', loadSubs);
    }
    const btnClear = $('#mzs-wa-clear');
    if (btnClear) {
      btnClear.addEventListener('click', async () => {
        if (!confirm('¿Eliminar TODOS los contactos WhatsApp? Esta acción no se puede deshacer.')) {
          return;
        }
        try {
          await apiJSON(`${API_N}/wa-clear${qs()}`, {
            method: 'POST',
            headers: auth(true),
            body: JSON.stringify({})
          });

          // очищаем локальный кэш и перерисовываем
          waSelectedManual.clear?.();
          waPage = 1;
          subsCache = { wa: {} };
          loadSubs();
        } catch (e) {
          alert(e.message || 'Error al vaciar la lista');
        }
      });
    }


    loadSubs();
    applyWaSearchFilter();
  }

  if (tok()) initOnce();

  document.addEventListener('mz:admin-auth', (e)=> {
    if (e?.detail?.ok) initOnce();
  });

  document.getElementById('ui-subs')
    ?.addEventListener('mz:pane:show', (ev)=> {
      const mod = ev?.detail?.mod;
      if (mod === 'subs') initOnce();
    });

})();