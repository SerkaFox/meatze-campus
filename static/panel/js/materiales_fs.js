/* static/panel/js/materiales_fs.js */
// ---- global helpers (used outside IIFE too) ----


window.getCookie = window.getCookie || function(name){
  const v = document.cookie.split(';')
    .map(s => s.trim())
    .find(s => s.startsWith(name + '='));
  return v ? decodeURIComponent(v.split('=')[1]) : '';
};

async function mzPostJSON(url, data, csrftoken){
  const r = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: JSON.stringify(data || {})
  });

  const txt = await r.text();
  let j = {};
  try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}

  if(!r.ok || !j.ok){
    console.error('[mzPostJSON FAIL]', {
      url,
      status: r.status,
      csrftoken_present: !!csrftoken,
      response_text: txt,
      response_json: j
    });
    throw new Error(j.error || j.message || txt || ('HTTP ' + r.status));
  }

  return j;
}
window.mzPostJSON = mzPostJSON;
function mzCsrfToken(){
  const fromInput =
    document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    document.querySelector('[data-csrf-token]')?.getAttribute('data-csrf-token') ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
    '';

  if (fromInput && fromInput.trim()) return fromInput.trim();

  const fromCookie = getCookie('csrftoken') || window.getCookie?.('csrftoken') || '';
  return (fromCookie || '').trim();
}
window.mzCsrfToken = mzCsrfToken;
(() => {
  'use strict';
  if (window.__MZ_MATERIALES_FS__) return;
  window.__MZ_MATERIALES_FS__ = true;
  // -----------------------------
  // utils
  // -----------------------------
  const $  = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

  function getCookie(name){
    const v = document.cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith(name+'='));
    return v ? decodeURIComponent(v.split('=')[1]) : '';
  }

  async function copyToClipboard(text){
    try{
      await navigator.clipboard.writeText(text);
      return true;
    }catch(e){
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch(_){}
      document.body.removeChild(ta);
      return true;
    }
  }

  function isValidNumericId(x){
    return /^\d+$/.test(String(x || '').trim());
  }

  // -----------------------------
  // 1) Breadcrumbs
  // -----------------------------
  (function initBreadcrumbs(){
    const bc = document.getElementById('mz-fold-bc');
    if(!bc) return;

    const path = (bc.getAttribute('data-path') || '').trim();
    if(!path) return;

    const aud  = encodeURIComponent(bc.getAttribute('data-aud') || 'alumnos');
    const mod  = encodeURIComponent(bc.getAttribute('data-mod') || '');
    const sort = encodeURIComponent(bc.getAttribute('data-sort') || 'new');

    const parts = path.split('/').filter(Boolean);
    let acc = '';

    parts.forEach((p)=>{
      acc = acc ? (acc + '/' + p) : p;

      const sep = document.createElement('span');
      sep.className = 'mz-bc-sep';
      sep.textContent = '›';
      bc.appendChild(sep);

      const a = document.createElement('a');
      a.className = 'mz-bc';
      a.textContent = p;
      a.href = `?tab=materiales&aud=${aud}&p=${encodeURIComponent(acc)}&sort=${sort}`;
      bc.appendChild(a);
    });
  })();


  // -----------------------------
  // 2) Preview modal
  // -----------------------------
  (function initPreview(){
    const modal = document.getElementById('mz-preview');
    const body  = document.getElementById('mz-prev-body');
    const title = document.getElementById('mz-prev-title');
    const openA = document.getElementById('mz-prev-open');
    const closeBtn = modal ? modal.querySelector('button[data-close]') : null;
    if(!modal || !body || !title || !openA) return;

    let lastFocus = null;

    function openPreview(url, name){
      lastFocus = document.activeElement;
      title.textContent = name || 'Vista previa';
      openA.href = url;

      body.innerHTML = '';
      const u = (url || '').toLowerCase();

      const isPdf = u.includes('.pdf') || u.includes('inline=1');
      const isImg = u.match(/\.(png|jpg|jpeg|webp|gif)(\?|$)/);

      if(isPdf){
        const ifr = document.createElement('iframe');
        ifr.src = url;
        body.appendChild(ifr);
      } else if(isImg){
        const img = document.createElement('img');
        img.src = url;
        img.alt = title.textContent;
        body.appendChild(img);
      } else {
        body.innerHTML = '<div style="padding:14px;color:#cbd5e1">No hay vista previa para este tipo. Usa “Abrir/Descargar”.</div>';
      }

      modal.classList.remove('is-hidden');
      modal.setAttribute('aria-hidden','false');
      document.body.style.overflow = 'hidden';
      (closeBtn || openA).focus();
    }

    function closePreview(){
      if(lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
      lastFocus = null;

      modal.classList.add('is-hidden');
      modal.setAttribute('aria-hidden','true');
      body.innerHTML = '';
      document.body.style.overflow = '';
    }

    modal.addEventListener('click', (e)=>{
      if(e.target.matches('[data-close]') || e.target.closest('[data-close]')) closePreview();
    });

    document.addEventListener('keydown', (e)=>{
      if(e.key === 'Escape' && !modal.classList.contains('is-hidden')) closePreview();
    });

    document.addEventListener('click', (e)=>{
      const a = e.target.closest('a[data-preview]');
      if(!a) return;
      e.preventDefault();
      openPreview(a.getAttribute('href'), a.getAttribute('data-name') || a.textContent.trim());
    });
  })();


  // -----------------------------
  // 3) Public share link (копировать ссылку)
  // -----------------------------
  (function initCopyPublicLink(){
    async function postJSON(url){
      // APPEND_SLASH safe
      if (url && !url.endsWith('/')) url += '/';
      const r = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-Requested-With':'XMLHttpRequest' }
      });
      const txt = await r.text();
      let j = {};
      try { j = txt ? JSON.parse(txt) : {}; } catch(_){}
      if (!r.ok) throw new Error(j.error || j.message || ('HTTP ' + r.status));
      return j;
    }

    document.addEventListener('click', async (e)=>{
      const btn = e.target.closest('[data-action="materials.copy_public_link"]');
      if (!btn) return;

      const shareUrl = btn.getAttribute('data-share-url');
      if (!shareUrl) {
        alert('Falta data-share-url en el botón');
        return;
      }

      btn.disabled = true;
      const old = btn.textContent;
      btn.textContent = 'Generando...';

      try{
        const j = await postJSON(shareUrl);
        const publicUrl = j.url;
        if (!publicUrl) throw new Error('Respuesta sin url');

        await copyToClipboard(publicUrl);

        btn.textContent = 'Copiado ✓';
        setTimeout(()=>{ btn.textContent = old; btn.disabled = false; }, 900);
      }catch(err){
        btn.textContent = 'Error';
        console.error(err);
        setTimeout(()=>{ btn.textContent = old; btn.disabled = false; }, 1200);
        alert('No se pudo generar el enlace: ' + (err.message || err));
      }
    });
  })();

// =====================================
// TREE: toggle by arrow AND by name
// =====================================
(function initTreeToggleByName(){
  document.addEventListener('click', (e)=>{
    const link = e.target.closest('.mz-tree-folder');
    if(!link) return;

    // если кликнули по кнопкам/экшенам внутри строки — не трогаем
    if (e.target.closest('.mz-tree-actions, button, [data-action], [data-toggle]')) return;

    const node = link.closest('.mz-tree-node');
    if(!node) return;

    const btn = node.querySelector('[data-toggle]');
    const kids = node.querySelector(':scope > .mz-tree-children');
    if(!btn || !kids) return;

    // ✅ не переходим по ссылке — работаем как toggle
    e.preventDefault();
    e.stopPropagation();

    btn.click(); // делегируем на твою существующую логику, включая localStorage
  }, true); // capture=true чтобы сработало раньше возможных других обработчиков
})();


  // -----------------------------
  // 4) Tree open/close persistence
  // -----------------------------
  (function initTreeOpenState(){
    const root = document.querySelector('.mz-tree');
    if(!root) return;

    const KEY = 'mz_tree_open_v1';

    function loadState(){
      try { return JSON.parse(localStorage.getItem(KEY) || '{}') || {}; }
      catch(e){ return {}; }
    }
    function saveState(st){
      try { localStorage.setItem(KEY, JSON.stringify(st || {})); } catch(e){}
    }
    const state = loadState();

    // init
    $$('.mz-tree-node', root).forEach(nodeEl=>{
      const path = nodeEl.getAttribute('data-node') || '';
      const kids = $('.mz-tree-children', nodeEl);
      const btn  = $('[data-toggle]', nodeEl);
      if(!kids || !btn) return;

      const open = !!state[path];
      kids.hidden = !open;
      btn.textContent = open ? '▾' : '▸';
    });

    // toggle

	document.addEventListener('click', (e)=>{
	  const btn = e.target.closest('[data-toggle]');
	  if(!btn) return;

	  const nodeEl = btn.closest('.mz-tree-node');
	  if(!nodeEl) return;

	  const kids = nodeEl.querySelector(':scope > .mz-tree-children');
	  if(!kids) return;

	  const path = nodeEl.getAttribute('data-node') || '';
	  kids.hidden = !kids.hidden;

	  const openNow = !kids.hidden;
	  btn.textContent = openNow ? '▾' : '▸';

	  state[path] = openNow ? 1 : 0;
	  saveState(state);
	});
  })();

  // -----------------------------
  // X) Cards view: click folder card -> show files below (move DOM container)
  // -----------------------------
  (function initFolderCardsPanel(){
    const grid = document.getElementById('mz-fold-grid');
    const panel = document.getElementById('mz-cards-panel');
    const body  = document.getElementById('mz-cards-body');
    const title = document.getElementById('mz-cards-title');
    if(!grid || !panel || !body || !title) return;

function mzSyncCardsFromTree(){
  const grid = document.getElementById('mz-fold-grid');
  const tree = document.querySelector('.mz-tree');
  if(!grid || !tree) return;

  // map path -> nodeEl (верхний уровень) + виртуальный root
  const wanted = new Map();
  wanted.set('', { __root: true });

  const nodes = Array.from(tree.querySelectorAll(
  ':scope > .mz-tree-node[data-node], :scope > .mz-tree-rootfolders > .mz-tree-node[data-node]'
));
  nodes.forEach(n => {
    const p = (n.getAttribute('data-node') || '').trim();
    if(p) wanted.set(p, n);
  });

	function getRootFilesCount(){
	  // 1) если root смонтирован в карточках — считаем там
	  if (window.__MZ_CARDS_MOUNT_PATH__ === '' && window.__MZ_CARDS_MOUNT_EL__) {
		return window.__MZ_CARDS_MOUNT_EL__
		  .querySelectorAll(':scope > .mz-tree-file[data-drag-file], :scope > .mz-tree-file[data-file-id]')
		  .length;
	  }

	  // 2) иначе ищем существующий rootfiles ГДЕ УГОДНО в документе
	  let rootFiles = document.querySelector('.mz-tree-rootfiles');

	  // 3) если его вообще нет — создаём в дереве
	  if(!rootFiles){
		const tree = document.querySelector('.mz-tree');
		if(!tree) return 0;
		rootFiles = document.createElement('div');
		rootFiles.className = 'mz-tree-rootfiles';
		tree.prepend(rootFiles);
	  }

	  return rootFiles
		.querySelectorAll(':scope > .mz-tree-file[data-drag-file], :scope > .mz-tree-file[data-file-id]')
		.length;
	}

	function createCard(path, node){
	  const isRoot = (path === '');
	  const name = isRoot
		? 'Raíz'
		: ((node.getAttribute('data-folder-name') || path.split('/').pop() || path).trim());

	  const locked = isRoot ? false : (node.getAttribute('data-locked') === '1');

	  const btn = document.createElement('button');
	  btn.type = 'button';
	  btn.className = 'mz-fold-card' + (locked ? ' is-locked' : '');
	  btn.setAttribute('data-open-path', path);
	  btn.setAttribute('data-path', path);
	  btn.setAttribute('data-drop-folder', path);
	  btn.title = isRoot ? 'Abrir raíz' : 'Abrir';

	  btn.innerHTML = `
		<a href="#"
		   class="mz-fold-zip"
		   title="Descargar ZIP de esta carpeta"
		   data-action="materials.zip.folder"
		   data-codigo="${(window.__MZ_CURSO_CODIGO__||'')}"
		   data-aud="${(window.__MZ_AUD__||'alumnos')}"
		   data-path="${path}">⬇️</a>

		<div class="mz-fold-ico">${isRoot ? '🏠' : '📁'}</div>
		<div class="mz-fold-name"></div>

		<div class="mz-fold-meta">
		  <span class="mz-fold-count" data-count>0</span>
		  <span class="mz-fold-badge" hidden>Módulo</span>
		</div>
	  `;

	  btn.querySelector('.mz-fold-name').textContent = name;

	  const badge = btn.querySelector('.mz-fold-badge');
	  if(locked){
		badge.hidden = false;
		badge.textContent = 'Módulo';
	  } else {
		badge.hidden = true;
	  }

	  return btn;
	}

  // 1) удалить карточки, которых больше нет в дереве (кроме root, он path="")
  Array.from(grid.querySelectorAll('.mz-fold-card[data-path]')).forEach(card=>{
    const p = (card.getAttribute('data-path') || '');
    if(p !== '' && !wanted.has(p)) card.remove();
  });

  // 2) добавить/обновить карточки
  wanted.forEach((node, path)=>{
    const isRoot = (path === '');
    let card = grid.querySelector(`.mz-fold-card[data-path="${CSS.escape(path)}"]`);

    if(!card){
      card = createCard(path, node.__root ? null : node);
      // root — лучше первым
      if(isRoot) grid.prepend(card);
      else grid.appendChild(card);
    }

    // обновим имя/locked (root не трогаем по locked)
    if(!isRoot){
      const name = (node.getAttribute('data-folder-name') || '').trim();
      if(name){
        const nameEl = card.querySelector('.mz-fold-name');
        if(nameEl) nameEl.textContent = name;
      }

      const locked = (node.getAttribute('data-locked') === '1');
      card.classList.toggle('is-locked', locked);

      const badge = card.querySelector('.mz-fold-badge');
      if(badge){
        badge.hidden = !locked;
        if(locked) badge.textContent = 'Módulo';
      }
    } else {
      // root всегда не locked
      card.classList.remove('is-locked');
      const badge = card.querySelector('.mz-fold-badge');
      if(badge) badge.hidden = true;
    }

    // count
    const cntEl = card.querySelector('[data-count]');
    if(cntEl){
      if(isRoot){
        cntEl.textContent = String(getRootFilesCount());
      } else {
        const c = node.querySelector('.mz-tree-count');
        cntEl.textContent = c ? (c.textContent || '0') : '0';
      }
    }
  });
  // 3) reorder cards to match tree order (root first + DOM order)
const order = [''].concat(nodes.map(n => (n.getAttribute('data-node')||'').trim()).filter(Boolean));

order.forEach(path=>{
  const card = grid.querySelector(`.mz-fold-card[data-path="${CSS.escape(path)}"]`);
  if(card) grid.appendChild(card);  // appendChild moves if already there
});
}




// экспортируем, чтобы дергать из других мест
window.mzMaterialsSyncCardsFromTree = mzSyncCardsFromTree;
// ✅ первичный синк после построения DOM
if (document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', ()=> mzSyncCardsFromTree());
} else {
  mzSyncCardsFromTree();
}
    // текущая “подключенная” папка
    let current = null;        // path string
    let movedEl = null;        // DOM element moved into panel
    let placeholder = null;    // comment node where it was

    function ensureRootFilesContainer(){
      let root = document.querySelector('.mz-tree-rootfiles');
      if(!root){
        root = document.createElement('div');
        root.className = 'mz-tree-rootfiles';
        const tree = document.querySelector('.mz-tree');
        if(tree) tree.prepend(root);
      }
      return root;
    }

    function getFilesContainer(path){
      const p = (path || '').trim().replace(/^\/+|\/+$/g,'');
      if(!p){
        return ensureRootFilesContainer();
      }
      const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(p)}"]`);
      if(!node) return null;

      let kids = node.querySelector(':scope > .mz-tree-children');
      if(!kids){
        kids = document.createElement('div');
        kids.className = 'mz-tree-children';
        node.appendChild(kids);
      }

      // раскрыть визуально “на всякий”
      kids.hidden = false;
      const tgl = node.querySelector('[data-toggle]');
      if(tgl) tgl.textContent = '▾';

      return kids;
    }

    function restorePrevious(){
      if(!movedEl || !placeholder) return;
      const parent = placeholder.parentNode;
      if(parent){
        parent.insertBefore(movedEl, placeholder);
        placeholder.remove();
      }
      movedEl = null;
      placeholder = null;
      current = null;
	  window.__MZ_CARDS_MOUNT_PATH__ = null;
	  window.__MZ_CARDS_MOUNT_EL__   = null;
    }

    function mountPath(path){
      const p = (path || '').trim().replace(/^\/+|\/+$/g,'');
      const target = getFilesContainer(p);
      if(!target) return;

      // если уже выбран этот же путь — просто показать/скролл
      if(current === p){
        panel.hidden = false;
        panel.scrollIntoView({behavior:'smooth', block:'start'});
        return;
      }

      // вернуть предыдущую папку на место
      restorePrevious();

      // поставить “якорь” на старом месте и перенести kids в панель
      placeholder = document.createComment('mz-cards-anchor');
      target.parentNode.insertBefore(placeholder, target);

      movedEl = target;
	  window.__MZ_CARDS_MOUNT_PATH__ = p;     // текущий путь в панели
	  window.__MZ_CARDS_MOUNT_EL__   = movedEl; // сам контейнер (.mz-tree-children)
      body.innerHTML = '';
      body.appendChild(movedEl);

      current = p;
      panel.hidden = false;

      // заголовок
      title.textContent = p ? `Archivos: ${p}` : 'Archivos: Raíz';

      // обновим data-parent у кнопок “Subir aquí / Nueva carpeta”
      panel.querySelectorAll('[data-action="folder.upload.here"], [data-action="folder.create.here"]').forEach(btn=>{
        btn.setAttribute('data-parent', p);
      });

      // важно: заново привязать drop targets (карточки тоже их имеют)
      window.mzMaterialsFsBindDropTargets?.();
      window.mzMaterialsReindexSearch?.();

    }
	window.mzMaterialsMountPath = mountPath;
    // клик по карточке
	grid.addEventListener('click', (e)=>{
	  // ✅ если клик по ZIP — не открываем карточку (пусть сработает initZipButtons)
	  if (e.target.closest('[data-action="materials.zip.folder"], [data-action="materials.zip.all"], .mz-fold-zip')) {
		return;
	  }

	  const card = e.target.closest('.mz-fold-card[data-open-path]');
	  if(!card) return;
	  e.preventDefault();
	  mountPath(card.getAttribute('data-open-path') || '');
	});

    // стартовое состояние: показываем текущую папку, если хочешь
		const bc = document.getElementById('mz-fold-bc');
		const initial = bc ? (bc.getAttribute('data-path') || '') : '';

		function isCardsLayout(){
		  const cardsWrap = document.getElementById('mz-cards-wrap');
		  return cardsWrap && !cardsWrap.hidden;
		}

		function ensureMountAccordingToLayout(){
		  if(isCardsLayout()){
			mountPath(initial);
		  } else {
			// В режиме дерева НЕ трогаем DOM: возвращаем всё назад
			restorePrevious();
			panel.hidden = true;
		  }
		  window.mzMaterialsSyncCardsFromTree?.();
		}

		// 1) при загрузке — монтируем только если реально cards
		ensureMountAccordingToLayout();

		// 2) при переключении layout — тоже
		document.addEventListener('click', (e)=>{
		  const btn = e.target.closest('[data-layout]');
		  if(!btn) return;
		  // даём layout-toggle сначала скрыть/показать блоки
		  setTimeout(ensureMountAccordingToLayout, 0);
		});
  })();
  
  
(function initZipButtons(){
  if (window.__MZ_ZIP_BTNS__) return;
  window.__MZ_ZIP_BTNS__ = true;

  function buildZipUrl({codigo, aud, path, scope}){
    const base = (window.__MZ_ZIP_URL__ || '/panel/materiales/zip/');
    const u = new URL(base, location.origin);

    u.searchParams.set('codigo', (codigo||'').trim());
    u.searchParams.set('aud', (aud||'alumnos').trim());
    u.searchParams.set('scope', scope || 'folder');

    if(scope === 'folder' || scope === 'root'){
      u.searchParams.set('p', (path||'').trim()); // root => ''
    }
    return u.toString();
  }

  function niceSpanishError(err, extra){
    // err: "module_disabled" | "no_files" | etc
    if(err === 'module_disabled'){
      return `
        <div style="display:flex; gap:12px; align-items:flex-start">
          <div style="font-size:22px">⛔</div>
          <div>
            <div style="font-weight:900; color:#fee2e2">Acceso denegado</div>
            <div style="margin-top:6px">
              No tienes permiso para descargar materiales de este módulo.
              <br>
              <span style="opacity:.9">Si crees que es un error, avisa a tu profesor/a.</span>
            </div>
          </div>
        </div>
      `;
    }
    if(err === 'no_files'){
      return `
        <div style="display:flex; gap:12px; align-items:flex-start">
          <div style="font-size:22px">📭</div>
          <div>
            <div style="font-weight:900; color:#e5e7eb">No hay archivos</div>
            <div style="margin-top:6px; opacity:.95">
              Esta carpeta no contiene archivos descargables.
            </div>
          </div>
        </div>
      `;
    }
    // fallback
    return `
      <div style="display:flex; gap:12px; align-items:flex-start">
        <div style="font-size:22px">⚠️</div>
        <div>
          <div style="font-weight:900; color:#e5e7eb">No se pudo completar</div>
          <div style="margin-top:6px; opacity:.95">
            ${extra || 'No tienes permisos o ocurrió un error al generar el ZIP.'}
          </div>
        </div>
      </div>
    `;
  }

  async function downloadZip(url){
    let r, blob, filename;

    try{
      r = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: { 'X-Requested-With': 'XMLHttpRequest' } // чтобы на сервере различать если надо
      });

      if(!r.ok){
        // пробуем JSON
        let j = null;
        try { j = await r.json(); } catch(_){}

        const err = (j && (j.error || j.message)) ? (j.error || j.message) : ('HTTP ' + r.status);

		if (window.mzIsDownloadForbidden?.(j, r.status)) {
		  window.mzDownloadBlocked?.(j?.reason || j?.error || 'forbidden');
		  return;
		}

        window.mzShowModal?.({
          title: 'No se pudo descargar',
          variant: 'info',
          html: niceSpanishError(j?.error || '', err)
        });
        return;
      }

      blob = await r.blob();

      // filename из headers (если есть)
      const cd = r.headers.get('Content-Disposition') || '';
      const m = cd.match(/filename="([^"]+)"/i);
      filename = m ? m[1] : 'materiales.zip';

      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(()=> URL.revokeObjectURL(objUrl), 1200);

    }catch(e){
      console.error(e);
      window.mzShowModal?.({
        title: 'Error de red',
        variant: 'info',
        html: `
          <div style="display:flex; gap:12px; align-items:flex-start">
            <div style="font-size:22px">📡</div>
            <div>
              <div style="font-weight:900; color:#e5e7eb">No se pudo conectar</div>
              <div style="margin-top:6px; opacity:.95">
                Revisa tu conexión e inténtalo de nuevo.
              </div>
            </div>
          </div>
        `
      });
    }
  }

  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('[data-action="materials.zip.folder"]');
    if(!btn) return;
    e.preventDefault();
    e.stopPropagation();

    const path = (btn.getAttribute('data-path') || '').trim();
    const scope = path ? 'folder' : 'root';

    const url = buildZipUrl({
      codigo: btn.getAttribute('data-codigo'),
      aud: btn.getAttribute('data-aud'),
      path,
      scope
    });

    downloadZip(url);
  });

  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('[data-action="materials.zip.all"]');
    if(!btn) return;
    e.preventDefault();

    const url = buildZipUrl({
      codigo: btn.getAttribute('data-codigo'),
      aud: btn.getAttribute('data-aud'),
      scope: 'all'
    });

    downloadZip(url);
  });
})();


function mzBytesHuman(n){
  const num = Number(n || 0);
  if (num < 1024) return `${num} B`;
  if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
  if (num < 1024 * 1024 * 1024) return `${(num / 1024 / 1024).toFixed(1)} MB`;
  return `${(num / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

window.mzBytesHuman = mzBytesHuman;

window.mzGetCursoCodigo = function(){
  const m = location.pathname.match(/\/curso\/([^/]+)\//);
  return m ? decodeURIComponent(m[1]) : '';
};

window.mzGoogleDriveImportUrl = function(){
  const codigo = window.mzGetCursoCodigo();
  if(!codigo) throw new Error('No se pudo detectar código del curso');
  return `/alumno/curso/${encodeURIComponent(codigo)}/materiales/drive/import/`;
};

window.mzUploadApiBase = function(){
  const codigo = window.mzGetCursoCodigo();
  if(!codigo) throw new Error('No se pudo detectar código del curso en la URL');
  return `/alumno/curso/${encodeURIComponent(codigo)}/materiales/upload`;
};
const BIG_UPLOAD_THRESHOLD = 100 * 1024 * 1024; // 100 MB
const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB


function mzUploadInitUrl(){
  return mzUploadApiBase() + '/init/';
}

function mzUploadChunkUrl(){
  return mzUploadApiBase() + '/chunk/';
}

function mzUploadCompleteUrl(){
  return mzUploadApiBase() + '/complete/';
}
  // -----------------------------
  // 5) Drag & Drop move file (teacher)
  // -----------------------------
  (function initDnDMove(){
		function bumpCountCascadeTotal(path, delta){
		  const parts = (path||'').split('/').filter(Boolean);
		  let acc = '';
		  for(const p of parts){
			acc = acc ? (acc + '/' + p) : p;
			bumpCount(acc, delta, 'total');
		  }
		}
			  
    // “teacher mode” — если есть хоть один data-drop-folder
    const isTeacher = !!document.querySelector('[data-drop-folder]');
    if(!isTeacher) return;

    let dragFileId = null;
    let dragEl = null;

    function findTargetContainer(targetPath){
      // targetPath == "" => root
      if (!targetPath) {
        let root = document.querySelector('.mz-tree-rootfiles');
        if (!root){
          root = document.createElement('div');
          root.className = 'mz-tree-rootfiles';
          const tree = document.querySelector('.mz-tree');
          if (tree) tree.prepend(root);
        }
        return root;
      }
		const p = (targetPath || '').trim().replace(/^\/+|\/+$/g,'');

		// если это папка, открытая в карточках — возвращаем панельный контейнер
		if (window.__MZ_CARDS_MOUNT_PATH__ === p && window.__MZ_CARDS_MOUNT_EL__) {
		  return window.__MZ_CARDS_MOUNT_EL__;
		}
      const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(p)}"]`);
      if (!node) return null;

      const kids = node.querySelector('.mz-tree-children');
      if (!kids) return null;

      // auto expand
      kids.hidden = false;
      const tgl = node.querySelector('[data-toggle]');
      if (tgl) tgl.textContent = '▾';

      return kids;
    }
	window.mzFindTargetContainer = findTargetContainer;

		function parseCountText(txt){
		  const s = String(txt || '').trim();
		  // ожидаем "a/b"
		  const m = s.match(/^(\d+)\s*\/\s*(\d+)$/);
		  if(m) return { direct: parseInt(m[1],10)||0, total: parseInt(m[2],10)||0, hasPair:true };

		  // если там просто число
		  const n = parseInt(s,10);
		  if(Number.isFinite(n)) return { direct:n, total:n, hasPair:false };

		  return { direct:0, total:0, hasPair:false };
		}

		// mode: 'direct' | 'total' | 'both'
		function bumpCount(path, delta, mode='total'){
		  if (!path) return;
		  const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(path)}"]`);
		  if (!node) return;

		  const c = node.querySelector('.mz-tree-count');
		  if (!c) return;

		  const cur = parseCountText(c.textContent);

		  // если показываем "a/b":
		  if(cur.hasPair){
			if(mode === 'direct' || mode === 'both') cur.direct = Math.max(0, cur.direct + delta);
			if(mode === 'total'  || mode === 'both') cur.total  = Math.max(0, cur.total  + delta);
			c.textContent = `${cur.direct}/${cur.total}`;
			return;
		  }

		  // если показываем просто число — ведём себя как раньше
		  const n = Math.max(0, (mode === 'direct' ? cur.direct : cur.total) + delta);
		  c.textContent = String(n);
		}

	// arm drag only when handle pressed
	document.addEventListener('pointerdown', (e)=>{
	  const h = e.target.closest('.mz-drag-handle');
	  if(!h) return;
	  const it = h.closest('.mz-tree-file[data-drag-file]');
	  if(!it) return;
	  it.__mzDragArmed = true;
	  setTimeout(()=>{ it.__mzDragArmed = false; }, 800);
	});

	document.addEventListener('dragstart', (e)=>{
	  const it = e.target.closest('.mz-tree-file[data-drag-file]');
	  if(!it) return;

	  if(!it.__mzDragArmed){
		e.preventDefault();
		return;
	  }
	  it.__mzDragArmed = false;

	  dragEl = it;
	  dragFileId = it.getAttribute('data-drag-file');

	  if(!isValidNumericId(dragFileId)){
		dragEl = null;
		dragFileId = null;
		e.preventDefault();
		return;
	  }

	  it.classList.add('is-dragging');

	  e.dataTransfer.effectAllowed = 'move';
	  e.dataTransfer.setData('text/plain', String(dragFileId));
	  e.dataTransfer.setData('application/x-mz-file-id', String(dragFileId));
	});

	document.addEventListener('dragend', ()=>{
	  if(dragEl) dragEl.classList.remove('is-dragging');
	  dragEl = null;
	  dragFileId = null;
	  document.querySelectorAll('.is-drop-ok,.is-drop-bad')
		.forEach(x=>x.classList.remove('is-drop-ok','is-drop-bad'));
	});
    // bind to all drop targets currently in DOM
    function bindDropTargets(){
      document.querySelectorAll('[data-drop-folder]').forEach(folderEl=>{
		  
        if (folderEl.__mz_drop_bound) return;
        folderEl.__mz_drop_bound = true;

			folderEl.addEventListener('dragenter', (e)=>{
			  e.preventDefault();
			  const hasFiles = e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files');
			  if(!dragFileId && !hasFiles) return;
			  folderEl.classList.add(hasFiles ? 'is-drop-upload' : 'is-drop-ok');
			});

			folderEl.addEventListener('dragover', (e)=>{
			  e.preventDefault();
			  const hasFiles = e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files');
			  if(!dragFileId && !hasFiles) return;
			  e.dataTransfer.dropEffect = hasFiles ? 'copy' : 'move';
			});

        folderEl.addEventListener('dragleave', ()=>{
          folderEl.classList.remove('is-drop-ok','is-drop-bad','is-drop-upload');
        });

		folderEl.addEventListener('drop', async (e)=>{
		  e.preventDefault();
		  folderEl.classList.remove('is-drop-ok','is-drop-bad','is-drop-upload');

		  console.log('[DROP]', {
			targetPath: folderEl.getAttribute('data-drop-folder') || '',
			files: e.dataTransfer?.files?.length || 0,
			types: Array.from(e.dataTransfer?.types || []),
			items: e.dataTransfer?.items?.length || 0,
			dragFileId
		  });

		  const targetPath = folderEl.getAttribute('data-drop-folder') || '';
		  // ✅ это перенос папки, не обрабатываем здесь
		  const folderDragPath = e.dataTransfer?.getData('text/mz-folder') || '';
		  if (folderDragPath) {
			return;
		  }
		  // 1) upload local files
		  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length){
			try{
			  await uploadFilesToFolder(e.dataTransfer.files, targetPath);
			}catch(err){
			  console.error(err);
			  alert('No se pudo subir archivos: ' + (err.message || err));
			}
			return;
		  }


			  // 2) move existing file
			  const rawId =
				dragFileId ||
				e.dataTransfer.getData('application/x-mz-file-id') ||
				e.dataTransfer.getData('text/plain') ||
				e.dataTransfer.getData('text');

			  if(!isValidNumericId(rawId)){
				console.warn('DROP ignored: not a file id', rawId);
				return;
			  }
			  const fileId = String(rawId).trim();
          

          let fileEl = document.querySelector(`[data-drag-file="${CSS.escape(fileId)}"]`);
          if(!fileEl){
            console.warn('file element not found for', fileId);
            return;
          }
		const srcNode = fileEl.closest('.mz-tree-node[data-node]');
		const srcPath = (srcNode ? (srcNode.getAttribute('data-node') || '') : '').trim().replace(/^\/+|\/+$/g,'');
		const dstPath = (targetPath || '').trim().replace(/^\/+|\/+$/g,'');

          const form = new FormData();
          form.append('action', 'file_move');
          form.append('file_id', fileId);
          form.append('target_path', targetPath);
			console.log('[MZ DND] drop rawId', {
			  dragFileId,
			  app: e.dataTransfer.getData('application/x-mz-file-id'),
			  text: e.dataTransfer.getData('text/plain'),
			  text2: e.dataTransfer.getData('text'),
			});
          try{
            const r = await fetch(window.location.pathname + window.location.search, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'X-CSRFToken': mzCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
              },
              body: form
            });

            const raw = await r.text();
            let j = {};
            try { j = raw ? JSON.parse(raw) : {}; } catch(_) {}

            if(!r.ok || !j.ok) throw new Error(j.error || ('HTTP ' + r.status));

            // move in UI
            const targetContainer = findTargetContainer(targetPath);
            if (targetContainer){
              targetContainer.appendChild(fileEl);
            } else {
              // если list-view без дерева — просто уберём
              fileEl.remove();
            }

            // optional updates from backend
            if (j.module_key !== undefined) {
              fileEl.dataset.module = j.module_key || '';
              const tag = fileEl.querySelector('.mz-mat-tag, .mz-tree-modtag');
              if (tag) {
                tag.textContent = j.module_key || 'Sin módulo';
                tag.classList.toggle('muted', !j.module_key);
              }
            }

            if (j.file_html) {
              fileEl.outerHTML = j.file_html;
              fileEl = document.querySelector(`[data-drag-file="${CSS.escape(fileId)}"]`);
            }

// ✅ обновляем folder-атрибут, чтобы поиск показывал реальный путь
if (fileEl){
  fileEl.setAttribute('data-folder', dstPath);
  fileEl.dataset.folder = dstPath;
}

// ✅ обновить индекс поиска сразу
window.mzMaterialsReindexSearch?.();

			if (srcPath !== dstPath){

			  // direct: минус/плюс только для НЕ-root папок (root не имеет .mz-tree-count)
			  if (srcPath) bumpCount(srcPath, -1, 'direct');
			  if (dstPath) bumpCount(dstPath, +1, 'direct');

			  // total: каскад вверх тоже только для НЕ-root
			  if (srcPath) bumpCountCascadeTotal(srcPath, -1);
			  if (dstPath) bumpCountCascadeTotal(dstPath, +1);

			  // root-count и карточки — берём из DOM, просто пересинхроним
			  window.mzMaterialsSyncCardsFromTree?.();
			  window.mzCleanupEmptyPlaceholders?.();
			}

          }catch(err){
            console.error(err);
            alert('No se pudo mover el archivo: ' + (err.message || err));
          }
        });
      });
    }

    bindDropTargets();

function postFormXHR(url, formData, csrftoken, { onProgress } = {}){
  return new Promise((resolve, reject)=>{
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.withCredentials = true;

    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    if (csrftoken) xhr.setRequestHeader('X-CSRFToken', csrftoken);

    if (xhr.upload && typeof onProgress === 'function'){
      xhr.upload.addEventListener('progress', (ev)=>{
        if(!ev.lengthComputable) return;
        onProgress({
          loaded: ev.loaded || 0,
          total: ev.total || 0,
          percent: ev.total ? (ev.loaded / ev.total * 100) : 0
        });
      });
    }

    xhr.onload = () => {
      const txt = xhr.responseText || '';
      let j = {};
      try { j = txt ? JSON.parse(txt) : {}; } catch(_){}
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({ status: xhr.status, j, txt });
      } else {
        reject(new Error((j.error || j.message || txt || ('HTTP ' + xhr.status)).toString()));
      }
    };

    xhr.onerror = () => reject(new Error('Network error / blocked'));
    xhr.onabort = () => reject(new Error('Upload aborted'));

    xhr.send(formData);
  });
  
}


function shouldUseChunkUpload(file){
  return !!file && (file.size || 0) >= BIG_UPLOAD_THRESHOLD;
}

async function postJSON(url, data, csrftoken){
  const r = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: JSON.stringify(data || {})
  });

  const txt = await r.text();
  let j = {};
  try { j = txt ? JSON.parse(txt) : {}; } catch(_){}

  if(!r.ok || !j.ok){
    console.error('[postJSON FAIL]', {
      url,
      status: r.status,
      csrftoken_present: !!csrftoken,
      response_text: txt,
      response_json: j
    });
    throw new Error(j.error || j.message || txt || ('HTTP ' + r.status));
  }
  return j;
}

async function uploadFileInChunks(file, targetPath, jobId){
  const csrftoken = mzCsrfToken();
console.log('[chunk init]', {
  url: mzUploadInitUrl(),
  csrftoken: getCookie('csrftoken'),
  audience: (window.__MZ_AUD__ || 'alumnos'),
  targetPath
});
  // 1) init
  const initRes = await postJSON(mzUploadInitUrl(), {
    audience: (window.__MZ_AUD__ || 'alumnos'),
    folder_path: targetPath || '',
    filename: file.name,
    filesize: file.size,
    content_type: file.type || 'application/octet-stream',
    chunk_size: CHUNK_SIZE
  }, csrftoken);

  const uploadId = initRes.upload_id;
  if(!uploadId) throw new Error('upload_init sin upload_id');

  // 2) chunks
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

  for(let index = 0; index < totalChunks; index++){
    const start = index * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const blob = file.slice(start, end);

    const fd = new FormData();
    fd.append('upload_id', uploadId);
    fd.append('chunk_index', String(index));
    fd.append('total_chunks', String(totalChunks));
    fd.append('chunk', blob, file.name + `.part${index}`);

    await postFormXHR(mzUploadChunkUrl(), fd, csrftoken);

    const loaded = end;
    const percent = file.size ? (loaded / file.size * 100) : 0;

    mzUploadOverlay.setUploading(jobId, {
      percent,
      meta: `${mzBytesHuman(loaded)} / ${mzBytesHuman(file.size)} · 1 archivo`
    });
  }

  // 3) complete
  const doneRes = await postJSON(mzUploadCompleteUrl(), {
    upload_id: uploadId
  }, csrftoken);

  return doneRes;
}

async function uploadFilesToFolder(fileList, targetPath){
  const files = Array.from(fileList || []).filter(f => f && f.size >= 0);
  if(!files.length) return;

  const container = findTargetContainer(targetPath);
  const csrftoken = mzCsrfToken();

  for(const file of files){
    const totalBytes = file.size || 0;
    const jobId = mzUploadOverlay.addJob({
      name: file.name,
      meta: `0 / ${mzBytesHuman(totalBytes)} · 1 archivo`
    });

    try{
      let j;

      if(shouldUseChunkUpload(file)){
        j = await uploadFileInChunks(file, targetPath, jobId);
      } else {
        const fd = new FormData();
        fd.append('action', 'upload_files_ajax');
        fd.append('folder_path', targetPath || '');
        fd.append('audience', (window.__MZ_AUD__ || 'alumnos'));
        fd.append('files', file, file.name);

        const res = await postFormXHR(mzPostUrl(), fd, csrftoken, {
          onProgress: ({ loaded, total, percent }) => {
            const safeTotal = total || totalBytes || 0;
            mzUploadOverlay.setUploading(jobId, {
              percent,
              meta: `${mzBytesHuman(loaded)} / ${mzBytesHuman(safeTotal)} · 1 archivo`
            });
          }
        });

        j = res.j;
      }

      if(!j || !j.ok){
        throw new Error((j && (j.error || j.message)) || 'upload_failed');
      }

      if(container && Array.isArray(j.files)){
        let added = 0;
        for(const it of j.files){
          if(it && it.file_html){
            container.insertAdjacentHTML('afterbegin', it.file_html);
            added += 1;
          }
        }

        if(targetPath){
          bumpCount(targetPath, +added, 'direct');
          bumpCountCascadeTotal(targetPath, +added);
        }

        window.mzMaterialsSyncCardsFromTree?.();
        window.mzMaterialsFsBindDropTargets?.();
        window.mzMaterialsReindexSearch?.();
      }

      mzUploadOverlay.setDone(jobId, {
        meta: `${mzBytesHuman(totalBytes)} · 1 archivo`
      });

    }catch(err){
      mzUploadOverlay.setError(jobId, err.message || 'No se pudo subir archivo');
      throw err;
    }
  }
}

// ✅ чтобы кнопка “загрузить сюда” могла вызвать
window.mzMaterialsUploadFilesToFolder = uploadFilesToFolder;

    window.mzMaterialsFsBindDropTargets = bindDropTargets;
  })();


	// -----------------------------
	// 6) Create folder (AJAX) — supports "big" + "here"
	// -----------------------------
	(function initCreateFolder(){
	  const form = document.getElementById('mz-folder-create-form');
	  if(!form) return;

function hasDuplicateNameInParent(parentPath, name){
  const container = ensureChildrenContainer(parentPath || '');
  if(!container) return false;

  const wanted = (name || '').trim().toLowerCase();

  // берём только папки, которые являются прямыми детьми этого контейнера
  const siblings = Array.from(container.querySelectorAll(':scope > .mz-tree-node[data-folder-name]'));
  return siblings.some(n => ((n.getAttribute('data-folder-name') || '').trim().toLowerCase() === wanted));
}

	  async function createFolderAjax(parent, name){
		const fd = new FormData(form);
		fd.set('folder_parent', parent || '');
		fd.set('folder_name', name);

		const r = await fetch(window.location.pathname + window.location.search, {
		  method: 'POST',
		  credentials: 'include',
		  headers: {
			'X-CSRFToken': mzCsrfToken(),
			'X-Requested-With': 'XMLHttpRequest',
		  },
		  body: fd
		});

		// если бек вернул 302 -> почти наверняка не AJAX/CSRF; покажем полезный лог
		const txt = await r.text();
		let j = {};
		try { j = txt ? JSON.parse(txt) : {}; } catch(_){}

		if (!r.ok || !j.ok){
		  const err = j.error || j.message || ('HTTP ' + r.status);
		  throw new Error(err + (r.status === 302 ? ' (redirect 302: check AJAX headers/CSRF)' : ''));
		}
		return j;
	  }

	  function ensureChildrenContainer(parentPath){
		// parentPath == "" -> root folders container
		const p = (parentPath || '').trim().replace(/^\/+|\/+$/g,'');

		// если сейчас в карточках открыт именно этот parentPath — вставляем прямо в панель
		if (window.__MZ_CARDS_MOUNT_PATH__ === p && window.__MZ_CARDS_MOUNT_EL__) {
		  return window.__MZ_CARDS_MOUNT_EL__;
		}
		if(!parentPath){
		  let root = document.querySelector('.mz-tree-rootfolders');
		  if(!root){
			root = document.createElement('div');
			root.className = 'mz-tree-rootfolders';
			const tree = document.querySelector('.mz-tree');
			if(tree) tree.prepend(root);
		  }
		  return root;
		}

		const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(parentPath)}"]`);
		if(!node) return null;

		let kids = node.querySelector('.mz-tree-children');
		if(!kids){
		  kids = document.createElement('div');
		  kids.className = 'mz-tree-children';
		  node.appendChild(kids);
		}

		// раскрыть визуально
		kids.hidden = false;
		const tgl = node.querySelector('[data-toggle]');
		if(tgl) tgl.textContent = '▾';

		return kids;
	  }

	  document.addEventListener('click', async (e)=>{
		const btn =
		  e.target.closest('[data-action="folder.create.big"]') ||
		  e.target.closest('[data-action="folder.create.here"]');

		if(!btn) return;

		e.preventDefault();
		e.stopPropagation();

		const explicit = (btn.getAttribute('data-parent') || '').trim();

		const inferredFromNode =
		  btn.closest('.mz-tree-node[data-node]')?.getAttribute('data-node') || '';

		const inferredFromCards =
		  (window.__MZ_CARDS_MOUNT_PATH__ || '');

		const parent = (explicit || inferredFromNode || inferredFromCards || '')
		  .trim()
		  .replace(/^\/+|\/+$/g,''); // нормализуем
		const name = prompt('Nombre de la carpeta:');
		if(!name) return;
		if(hasDuplicateNameInParent(parent, name)){
		  alert('Ya existe una carpeta con ese nombre en esta ubicación.');
		  return;
		}
		try{
		  const j = await createFolderAjax(parent, name.trim());

		  if(j.node_html){
			const container = ensureChildrenContainer(j.parent_path ?? parent);
			if(container){
			  container.insertAdjacentHTML('afterbegin', j.node_html);
			  if(window.mzMaterialsFsBindDropTargets) window.mzMaterialsFsBindDropTargets();
			  if(window.mzMaterialsReindexSearch) window.mzMaterialsReindexSearch();
			  // после вставки узла дерева
				window.mzMaterialsSyncCardsFromTree?.();
			}
		  } else {
			console.warn('folder created but no node_html returned', j);
			// fallback: reload only if you want
			// location.reload();
		  }
		}catch(err){
		  console.error(err);
		  alert('No puedo crear carpeta. ' + (err.message || err));
		}
	  });
	})();


  // -----------------------------
  // 7) Tree sort (folders + files) without reload
  // -----------------------------
  (function initTreeSort(){
    const sortBar = document.querySelector('.mz-mat-sort');
    if(!sortBar) return;
		
	function computeFolderLatestTs(){
	  const tree = document.querySelector('.mz-tree');
	  if(!tree) return;

	  // 1) сброс
	  tree.querySelectorAll('.mz-tree-node[data-node]').forEach(n=>{
		n.dataset.latestTs = '0';
	  });

	  // 2) каждому файлу известен data-ts (у тебя есть)
	  //    поднимаем latest вверх по цепочке родителей
	  const files = Array.from(tree.querySelectorAll('.mz-tree-file[data-ts]'));
	  for(const f of files){
		const ts = parseInt(f.getAttribute('data-ts') || '0', 10) || 0;

		// файл может быть:
		// - внутри kids конкретной папки
		// - или в rootfiles (тогда ближайшей папки нет)
		let node = f.closest('.mz-tree-node[data-node]');
		while(node){
		  const cur = parseInt(node.dataset.latestTs || '0', 10) || 0;
		  if(ts > cur) node.dataset.latestTs = String(ts);
		  node = node.parentElement ? node.parentElement.closest('.mz-tree-node[data-node]') : null;
		}
	  }
	}

	function sortContainerFiles(container, mode){
	  const files = Array.from(container.querySelectorAll(':scope > .mz-tree-file'));
	  if(!files.length) return;

      const byName = (a,b)=> (a.dataset.name||'').localeCompare(b.dataset.name||'', undefined, {numeric:true, sensitivity:'base'});
      const byTs   = (a,b)=> (parseInt(a.dataset.ts||'0',10) - parseInt(b.dataset.ts||'0',10));

      let cmp = byName;
      if(mode === 'az') cmp = byName;
      if(mode === 'za') cmp = (a,b)=> -byName(a,b);
      if(mode === 'old') cmp = byTs;
      if(mode === 'new') cmp = (a,b)=> -byTs(a,b);

      files.sort(cmp);
      files.forEach(el=>container.appendChild(el));
    }

	function sortFolderNodes(container, mode){
	  const nodes = Array.from(container.querySelectorAll(':scope > .mz-tree-node'));
	  if(!nodes.length) return;

	  const getName = (el)=> (el.getAttribute('data-folder-name') || '').trim().toLowerCase();
	  const getLockedKey = (el)=> (el.getAttribute('data-locked') === '1' ? 0 : 1); // locked first как было
	  const getLatestTs = (el)=> parseInt(el.dataset.latestTs || '0', 10) || 0;

	  const byName = (a,b)=> getName(a).localeCompare(getName(b), undefined, {numeric:true, sensitivity:'base'});

	  const cmp = (a,b)=>{
		// 0) сначала модули (если хочешь оставить как было)
		const la = getLockedKey(a), lb = getLockedKey(b);
		if (la !== lb) return la - lb;

		// 1) режимы new/old: по “свежести” папки (max ts среди файлов внутри/в подпапках)
		if(mode === 'new' || mode === 'old'){
		  const ta = getLatestTs(a), tb = getLatestTs(b);
		  if(ta !== tb) return (mode === 'new') ? (tb - ta) : (ta - tb);
		  // если одинаково — стабильный тайбрейк по имени
		  return byName(a,b);
		}

		// 2) режимы az/za: по имени
		if(mode === 'za') return -byName(a,b);
		return byName(a,b);
	  };

	  nodes.sort(cmp);
	  nodes.forEach(n=>container.appendChild(n));
	}

    function applySort(mode){
		computeFolderLatestTs();
      const treeRoot = document.querySelector('.mz-tree');
      if (treeRoot) sortFolderNodes(treeRoot, mode);

      document.querySelectorAll('.mz-tree-node .mz-tree-children').forEach(kids=>{
        sortFolderNodes(kids, mode);
      });

      const rootFiles = document.querySelector('.mz-tree-rootfiles');
      if(rootFiles) sortContainerFiles(rootFiles, mode);

      document.querySelectorAll('.mz-tree-node .mz-tree-children').forEach(kids=>{
        sortContainerFiles(kids, mode);
      });

      sortBar.querySelectorAll('a.mz-pill').forEach(a=>a.classList.remove('is-act'));
      const active = sortBar.querySelector(`a[href*="sort=${mode}"]`);
      if(active) active.classList.add('is-act');
	  window.mzMaterialsSyncCardsFromTree?.();
    }

    sortBar.addEventListener('click', (e)=>{
      const a = e.target.closest('a[href*="sort="]');
      if(!a) return;

      const u = new URL(a.href, location.origin);
      const mode = u.searchParams.get('sort') || 'new';

      e.preventDefault();

      const cur = new URL(location.href);
      cur.searchParams.set('sort', mode);
      history.replaceState({}, '', cur);

      applySort(mode);
    });

    const curSort = new URLSearchParams(location.search).get('sort') || 'new';
    applySort(curSort);
  })();

})();



// -----------------------------
// 8) File search (tree) — show path + expand & scroll
// -----------------------------
(function initFileSearch(){
  const tree = document.querySelector('.mz-tree');
  if(!tree) return;

  // куда вставлять UI (можно поменять якорь)
  const host =
    document.querySelector('.mz-mat-sort') ||
    document.querySelector('.mz-mat-topbar') ||
    tree;

  // UI
  const wrap = document.createElement('div');
  wrap.className = 'mz-mat-search';
  wrap.innerHTML = `
    <div class="mz-search-row">
      <input class="mz-search-input" type="search" placeholder="Buscar archivo..." autocomplete="off">
      <button class="mz-search-clear" type="button" title="Limpiar">✕</button>
    </div>
    <div class="mz-search-results" hidden></div>
  `;
  host.parentNode.insertBefore(wrap, host.nextSibling);

  const inp = wrap.querySelector('.mz-search-input');
  const btnClear = wrap.querySelector('.mz-search-clear');
  const box = wrap.querySelector('.mz-search-results');

  // индекс файлов из DOM
	function buildIndex(){
	  const els = Array.from(document.querySelectorAll('.mz-tree-file[data-file-id], .mz-tree-file[data-drag-file]'));
	  return els.map(el => {
		const id = el.getAttribute('data-file-id') || el.getAttribute('data-drag-file') || '';
		const name = (el.getAttribute('data-name') || el.textContent || '').trim();

		// ✅ folder берём из DOM-места (истина), а data-folder — как fallback
		let folder = '';
		const node = el.closest('.mz-tree-node[data-node]');
		folder = node ? (node.getAttribute('data-node') || '').trim() : '';

		if(folder === ''){
		  folder = (el.getAttribute('data-folder') || '').trim();
		}
		return { el, id, name, folder };
	  }).filter(it => it.id);
	}
  let index = buildIndex();

  // Если у тебя дерево может динамически меняться (upload / move / ajax), можно вручную обновлять:
  window.mzMaterialsReindexSearch = () => { index = buildIndex(); };
// ✅ Авто-переиндексация при изменениях в дереве/панели
(function autoReindex(){
  const root = document.querySelector('.mz-tree');
  if(!root || !window.MutationObserver) return;

  let t = null;
  const schedule = ()=>{
    clearTimeout(t);
    t = setTimeout(()=>{ index = buildIndex(); }, 80);
  };

  const obs = new MutationObserver((mutations)=>{
    // если добавили/удалили/перенесли файлы — обновим индекс
    for(const m of mutations){
      if(m.type === 'childList'){
        schedule();
        break;
      }
      if(m.type === 'attributes' && (m.attributeName === 'data-folder' || m.attributeName === 'data-name')){
        schedule();
        break;
      }
    }
  });

  obs.observe(root, { childList:true, subtree:true, attributes:true, attributeFilter:['data-folder','data-name'] });
})();
  // раскрыть цепочку папок + проскроллить к файлу
  function openFolder(path){
    // path = "A/B/C" -> открыть A, A/B, A/B/C
    const parts = (path || '').split('/').filter(Boolean);
    let acc = '';
    parts.forEach(seg => {
      acc = acc ? (acc + '/' + seg) : seg;
      const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(acc)}"]`);
      if(!node) return;
      const kids = node.querySelector('.mz-tree-children');
      const tgl = node.querySelector('[data-toggle]');
      if(kids){
        kids.hidden = false;
        if(tgl) tgl.textContent = '▾';
      }
    });

    // плюс: синхронизируем localStorage открытий (твоя логика из initTreeOpenState)
    try{
      const KEY = 'mz_tree_open_v1';
      const st = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
      let acc2 = '';
      parts.forEach(seg => {
        acc2 = acc2 ? (acc2 + '/' + seg) : seg;
        st[acc2] = 1;
      });
      localStorage.setItem(KEY, JSON.stringify(st));
    }catch(_){}
  }

  function highlightAndScroll(el){
    el.classList.add('is-found');
    el.scrollIntoView({behavior:'smooth', block:'center'});
    setTimeout(()=>el.classList.remove('is-found'), 1400);
  }

  function renderResults(items, q){
    if(!q){
      box.hidden = true;
      box.innerHTML = '';
      return;
    }
    if(!items.length){
      box.hidden = false;
      box.innerHTML = `<div class="mz-search-empty">Nada encontrado</div>`;
      return;
    }

    const esc = (s)=> (s||'').replace(/[&<>"']/g, m => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    }[m]));

    box.hidden = false;
    box.innerHTML = items.slice(0, 30).map(it => {
      const path = it.folder ? it.folder : 'Raíz';
      return `
        <button type="button" class="mz-search-item"
                data-file-id="${esc(it.id)}"
                data-folder="${esc(it.folder)}">
          <div class="mz-search-name">${esc(it.name)}</div>
          <div class="mz-search-path">${esc(path)}</div>
        </button>
      `;
    }).join('');
  }

  let t = null;
  function onInput(){
    const q = (inp.value || '').trim().toLowerCase();
    clearTimeout(t);
    t = setTimeout(()=>{
      if(!q){ renderResults([], ''); return; }
      const res = index.filter(it => (it.name||'').toLowerCase().includes(q));
      renderResults(res, q);
    }, 120);
  }

  inp.addEventListener('input', onInput);

  btnClear.addEventListener('click', ()=>{
    inp.value = '';
    inp.focus();
    renderResults([], '');
  });

	box.addEventListener('click', (e)=>{
	  const btn = e.target.closest('.mz-search-item');
	  if(!btn) return;

	  const fileId = btn.getAttribute('data-file-id') || '';
	  const folder = btn.getAttribute('data-folder') || '';

	  // 1) Всегда раскрываем дерево (и сохраняем состояние)
	  openFolder(folder);

	  // 2) В карточки переключаемся ТОЛЬКО если пользователь уже в режиме карточек
	  const panel = document.getElementById('mz-cards-panel');
	  const cardsModeNow = panel && !panel.hidden; // <- ключевая проверка

	  if (cardsModeNow && typeof window.mzMaterialsMountPath === 'function') {
		window.mzMaterialsMountPath(folder || '');
	  }

	  // 3) Подсветка — ищем элемент где он реально сейчас (в дереве или в панели)
	  const el =
		document.querySelector(`.mz-tree-file[data-file-id="${CSS.escape(fileId)}"]`) ||
		document.querySelector(`.mz-tree-file[data-drag-file="${CSS.escape(fileId)}"]`) ||
		document.querySelector(`[data-drag-file="${CSS.escape(fileId)}"]`);

	  if(el) highlightAndScroll(el);
	});

})();
// -----------------------------
// UI: confirm modal (3 actions)
// -----------------------------
function mzConfirmFolderDelete({ title, html, actions }){
  // actions: [{id, label, cls, value}]
  let modal = document.getElementById('mz-confirm-modal');
  if(!modal){
    modal = document.createElement('div');
    modal.id = 'mz-confirm-modal';
    modal.className = 'mz-modal';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="mz-modal-card" role="dialog" aria-modal="true" aria-labelledby="mz-modal-title">
        <div class="mz-modal-head">
          <div id="mz-modal-title" class="mz-modal-title"></div>
          <button type="button" class="mz-modal-x" data-x aria-label="Cerrar">✕</button>
        </div>
        <div class="mz-modal-body" data-body></div>
        <div class="mz-modal-actions" data-actions></div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e)=>{
      if(e.target === modal) close(null); // click outside
      if(e.target.closest('[data-x]')) close(null);
    });
    document.addEventListener('keydown', (e)=>{
      if(!modal.hidden && e.key === 'Escape') close(null);
    });
  }

  const titleEl = modal.querySelector('#mz-modal-title');
  const bodyEl  = modal.querySelector('[data-body]');
  const actEl   = modal.querySelector('[data-actions]');

  titleEl.textContent = title || 'Confirmación';
  bodyEl.innerHTML = html || '';
  actEl.innerHTML = '';

  let resolver = null;
  function close(val){
    modal.hidden = true;
    document.body.style.overflow = '';
    if(resolver) resolver(val);
    resolver = null;
  }

  actions.forEach(a=>{
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `mzc-btn ghost ${a.cls||''}`.trim();
    btn.textContent = a.label;
    btn.addEventListener('click', ()=> close(a.value));
    actEl.appendChild(btn);
  });

  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  // фокус на первую “безопасную” кнопку или первую
  setTimeout(()=>{
    const first = actEl.querySelector('button');
    if(first) first.focus();
  }, 0);

  return new Promise((resolve)=>{ resolver = resolve; });
}
function mzGetRootFilesContainer(){
  let root = document.querySelector('.mz-tree-rootfiles'); // ✅ глобально
  if(!root){
    root = document.createElement('div');
    root.className = 'mz-tree-rootfiles';
    const tree = document.querySelector('.mz-tree');
    if(tree) tree.prepend(root);
  }
  return root;
}
window.mzGetRootFilesContainer = mzGetRootFilesContainer;


const mzUploadOverlay = (() => {
  let jobs = new Map();
  let seq = 1;
  let autoHideTimer = null;
  const cancelHandlers = new Map();

  const root = () => document.getElementById('mz-upl-pop');
  const mini = () => document.getElementById('mz-upl-pop-mini');
  const miniText = () => document.getElementById('mz-upl-pop-mini-text');
  const miniPct = () => document.getElementById('mz-upl-pop-mini-pct');
  const card = () => document.getElementById('mz-upl-pop-card');
  const list = () => document.getElementById('mz-upl-pop-list');
  const sub = () => document.getElementById('mz-upl-pop-sub');

  function ensureVisible(){
    const r = root();
    if(r) r.hidden = false;
  }

	function onCancel(id, handler){
	  if(!id || typeof handler !== 'function') return;
	  cancelHandlers.set(id, handler);
	}

  function open(){
    ensureVisible();
    const c = card();
    if(c) c.hidden = false;
  }

  function close(){
    const c = card();
    const r = root();
    if(c) c.hidden = true;
    if(r) r.hidden = true;
  }

  function clearAutoHide(){
    if(autoHideTimer){
      clearTimeout(autoHideTimer);
      autoHideTimer = null;
    }
  }

  function closeAll(){
    clearAutoHide();
	cancelHandlers.clear();
    jobs.clear();

    const c = card();
    const r = root();

    if(c) c.hidden = true;
    if(r) r.hidden = true;

    render();
  }

  function scheduleAutoHide(){
    clearAutoHide();

    autoHideTimer = setTimeout(()=>{
      const arr = Array.from(jobs.values());
      const active = arr.some(j => j.status === 'uploading' || j.status === 'preparing');
      const hasErrors = arr.some(j => j.status === 'error');

      if(active) return;
      if(hasErrors) return;

      jobs.clear();

      const c = card();
      const r = root();

      if(c) c.hidden = true;
      if(r) r.hidden = true;

      render();
    }, 4000);
  }

  function getSummary(){
    const arr = Array.from(jobs.values());
    const active = arr.filter(j => j.status === 'uploading' || j.status === 'preparing');
    const done = arr.filter(j => j.status === 'done');
    const errors = arr.filter(j => j.status === 'error');

    let pct = 0;
    if(active.length){
      pct = Math.round(active.reduce((s, j)=>s + (j.percent || 0), 0) / active.length);
    } else if(done.length && !errors.length){
      pct = 100;
    }

    return { active, done, errors, pct };
  }

  function renderMini(){
    const { active, done, errors, pct } = getSummary();
    const r = root();
    if(!r) return;

    if(!jobs.size){
      r.hidden = true;
      return;
    }

    r.hidden = false;
if(active.length){
  const first = active[0];
  if(miniText()) miniText().textContent = active.length === 1
    ? `Subiendo: ${first.name} · no cierres esta página`
    : `Subiendo ${active.length} archivo(s)… · no cierres esta página`;
  if(miniPct()) miniPct().textContent = `${pct}%`;
  return;
}
  
    if(errors.length){
      if(miniText()) miniText().textContent = `Errores: ${errors.length}`;
      if(miniPct()) miniPct().textContent = '!';
      return;
    }

    if(done.length){
      if(miniText()) miniText().textContent = `Carga completada`;
      if(miniPct()) miniPct().textContent = '100%';
    }
  }

  function renderList(){
    const el = list();
    if(!el) return;

    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (m) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[m]));

    const arr = Array.from(jobs.values()).sort((a,b)=> b.id - a.id);

    el.innerHTML = arr.map(j => `
      <div class="mz-upl-job ${j.status === 'done' ? 'is-done' : ''} ${j.status === 'error' ? 'is-error' : ''}" data-job-id="${j.id}">
        <div class="mz-upl-job-head">
          <div class="mz-upl-job-name" title="${esc(j.name || '')}">${esc(j.name || '')}</div>
          <div class="mz-upl-job-state">${esc(j.stateLabel || '')}</div>
        </div>
        <div class="mz-upl-job-bar"><i style="width:${Math.max(0, Math.min(100, j.percent || 0))}%"></i></div>
        <div class="mz-upl-job-meta">${esc(j.meta || '')}</div>
      </div>
    `).join('');

    const { active, done, errors } = getSummary();
    if(sub()){
      sub().textContent = `${active.length} activas · ${done.length} completadas · ${errors.length} con error`;
    }
  }

  function render(){
    renderMini();
    renderList();
  }

  function addJob({ name, meta } = {}){
    clearAutoHide();

    jobs = new Map(
      Array.from(jobs.entries()).filter(([, j]) => j.status !== 'done')
    );

    ensureVisible();

    const id = seq++;
    jobs.set(id, {
      id,
      name: name || 'Archivo',
      meta: meta || '',
      percent: 0,
      status: 'preparing',
      stateLabel: 'Preparando'
    });

    render();
    open();
    return id;
  }

  function updateJob(id, patch = {}){
    const j = jobs.get(id);
    if(!j) return;
    Object.assign(j, patch);
    render();
  }

  function setUploading(id, { percent = 0, meta = '' } = {}){
    updateJob(id, {
      status: 'uploading',
      stateLabel: `${Math.round(percent)}%`,
      percent,
      meta
    });
  }

  function setDone(id, { meta = '' } = {}){
    updateJob(id, {
      status: 'done',
      stateLabel: 'Completado',
      percent: 100,
      meta
    });
	cancelHandlers.delete(id);
    render();
    scheduleAutoHide();
  }

  function setError(id, message){
    updateJob(id, {
      status: 'error',
      stateLabel: 'Error',
      meta: message || 'Upload failed'
    });
	cancelHandlers.delete(id);
    open();
  }

  function bind(){
    mini()?.addEventListener('click', ()=>{
      const c = card();
      const r = root();
      if(!c || !r) return;

      r.hidden = false;
      c.hidden = !c.hidden;
    });

    document.getElementById('mz-upl-pop-hide')?.addEventListener('click', ()=>{
      const c = card();
      if(c) c.hidden = true;
    });

	document.getElementById('mz-upl-pop-close')?.addEventListener('click', ()=>{
	  const activeJob = Array.from(jobs.values()).find(j =>
		j.status === 'uploading' || j.status === 'preparing'
	  );

	  if(activeJob){
		const fn = cancelHandlers.get(activeJob.id);
		if(fn){
		  fn();
		  return;
		}
	  }

	  closeAll();
	});
  }
function hasActiveUploads(){
  return Array.from(jobs.values()).some(j =>
    j.status === 'uploading' || j.status === 'preparing'
  );
}
	return {
	  bind,
	  open,
	  close,
	  closeAll,
	  addJob,
	  updateJob,
	  setUploading,
	  setDone,
	  setError,
	  onCancel,
	  hasActiveUploads
	};
})();
window.mzUploadOverlay = mzUploadOverlay;

ensureUploadOverlayDom();
mzUploadOverlay.bind();
window.addEventListener('beforeunload', (e)=>{
  if (!window.mzUploadOverlay?.hasActiveUploads?.()) return;

  e.preventDefault();
  e.returnValue = '';
});
document.addEventListener('click', (e)=>{
  const a = e.target.closest('a[href]');
  if(!a) return;

  // новые вкладки / служебные ссылки не трогаем
  if (
    a.target === '_blank' ||
    e.ctrlKey || e.metaKey || e.shiftKey || e.altKey ||
    a.hasAttribute('download')
  ) return;

  if (!window.mzUploadOverlay?.hasActiveUploads?.()) return;

  const href = a.getAttribute('href') || '';
  if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

  const ok = confirm('Hay una carga en progreso. Si sales ahora, la subida puede interrumpirse. ¿Quieres salir de todos modos?');
  if(!ok){
    e.preventDefault();
    e.stopPropagation();
  }
}, true);

function ensureUploadOverlayDom(){
  let el = document.getElementById('mz-upl-pop');
  if(el) return el;

  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <div id="mz-upl-pop" class="mz-upl-pop" hidden aria-live="polite" aria-atomic="true">
      <button type="button" class="mz-upl-pop-mini" id="mz-upl-pop-mini">
        <span class="mz-upl-pop-mini-dot"></span>
        <span id="mz-upl-pop-mini-text">Subiendo archivos…</span>
        <span id="mz-upl-pop-mini-pct">0%</span>
      </button>

      <div class="mz-upl-pop-card" id="mz-upl-pop-card" hidden>
        <div class="mz-upl-pop-head">
          <div>
            <div class="mz-upl-pop-title">Cargas</div>
            <div class="mz-upl-pop-sub" id="mz-upl-pop-sub">0 activas</div>
          </div>

          <div class="mz-upl-pop-actions">
            <button type="button" class="mzc-btn ghost" id="mz-upl-pop-hide">Ocultar</button>
            <button type="button" class="mzc-btn ghost" id="mz-upl-pop-close" aria-label="Cerrar">✕</button>
          </div>
        </div>

        <div class="mz-upl-pop-list" id="mz-upl-pop-list"></div>
      </div>
    </div>
  `.trim();

  el = wrap.firstElementChild;
  document.body.appendChild(el);
  return el;
}

function normPath(p){
  return (p || '').trim().replace(/^\/+|\/+$/g,'');
}

function mzParseCountText(txt){
  const s = String(txt || '').trim();
  const m = s.match(/^(\d+)\s*\/\s*(\d+)$/);
  if(m) return { direct: parseInt(m[1],10)||0, total: parseInt(m[2],10)||0, hasPair:true };
  const n = parseInt(s,10);
  if(Number.isFinite(n)) return { direct:n, total:n, hasPair:false };
  return { direct:0, total:0, hasPair:false };
}

// mode: 'direct' | 'total' | 'both'
function mzBumpCount(path, delta, mode='total'){
  if (!path) return;
  const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(path)}"]`);
  const c = node ? node.querySelector('.mz-tree-count') : null;
  if(!c) return;

  const cur = mzParseCountText(c.textContent);

  if(cur.hasPair){
    if(mode === 'direct' || mode === 'both') cur.direct = Math.max(0, cur.direct + delta);
    if(mode === 'total'  || mode === 'both') cur.total  = Math.max(0, cur.total  + delta);
    c.textContent = `${cur.direct}/${cur.total}`;
  }else{
    const n = Math.max(0, (mode === 'direct' ? cur.direct : cur.total) + delta);
    c.textContent = String(n);
  }
}
window.mzBumpCount = mzBumpCount;
function mzBumpCountCascade(path, delta, mode='total'){
  const parts = (path||'').split('/').filter(Boolean);
  let acc = '';
  for(const p of parts){
    acc = acc ? (acc + '/' + p) : p;
    mzBumpCount(acc, delta, mode);
  }
}

// удобно для "total" по всей цепочке
function mzBumpCountCascadeTotal(path, delta){
  mzBumpCountCascade(path, delta, 'total');
}
window.mzBumpCountCascadeTotal = mzBumpCountCascadeTotal;
function mzCleanupEmptyPlaceholders(){
  document.querySelectorAll('.mz-tree-node').forEach(node=>{
    const kids = node.querySelector(':scope > .mz-tree-children');
    if(!kids) return;

    const hasFile = kids.querySelector('.mz-tree-file');
    const hasChildFolder = kids.querySelector('.mz-tree-node');
    let empty = kids.querySelector(':scope > .mz-tree-empty');

    if(!hasFile && !hasChildFolder){
      if(!empty){
        empty = document.createElement('div');
        empty.className = 'mz-tree-empty';
        empty.textContent = '— sin archivos —';
        kids.prepend(empty);
      }
    }else{
      if(empty) empty.remove();
    }
  });
}

window.mzCleanupEmptyPlaceholders = mzCleanupEmptyPlaceholders;

(function initFolderDeleteAjax(){
  document.addEventListener('submit', async (e)=>{
    const form = e.target.closest('form[data-ajax="folder-delete"]');
    if(!form) return;
    e.preventDefault();

    try {
      const path = (form.querySelector('input[name="path"]')?.value || form.dataset.path || '').trim();
      if(!path) return;

      const csrftoken = mzCsrfToken();

      async function post(mode){
        const fd = new FormData(form);
        fd.set('action', 'folder_delete');
        fd.set('path', path);
        fd.set('mode', mode);

        const r = await fetch(window.location.pathname + window.location.search, {
          method:'POST',
          credentials:'include',
          headers:{ 'X-CSRFToken': csrftoken, 'X-Requested-With':'XMLHttpRequest' },
          body: fd
        });

        const txt = await r.text();
        let j = {};
        try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
        return { r, j };
      }

      // 1) check
      let res = await post('check');

      if(res.r.ok && res.j.ok){
        const node = form.closest('.mz-tree-node');
        if(node) node.remove();
        window.mzMaterialsSyncCardsFromTree?.();
        window.mzCleanupEmptyPlaceholders?.();
        window.mzMaterialsReindexSearch?.();
        return;
      }

      if(res.r.status === 409 && res.j.error === 'folder_not_empty'){
        const files = res.j.files_count || 0;
        const subs  = res.j.subfolders_count || 0;

        const choice = await mzConfirmFolderDelete({
          title: 'Eliminar carpeta',
          html: `
            <div style="line-height:1.35">
              La carpeta <b>${path}</b> no está vacía.<br>
              <span>Archivos: <b>${files}</b>, Subcarpetas: <b>${subs}</b></span>
              <div style="margin-top:10px; opacity:.9">
                ¿Qué quieres hacer?
              </div>
            </div>
          `,
          actions: [
            { label:'Cancelar', value:null },
            { label:'Mover archivos al raíz', value:'move_root' },
            { label:'Eliminar TODO', value:'purge', cls:'danger' },
          ]
        });

        if(!choice) return;

        const rr = await post(choice);

        if(rr.r.ok && rr.j.ok){
          const node = form.closest('.mz-tree-node');
          if(!node) return;

          if(choice === 'move_root'){
            const rootFiles = mzGetRootFilesContainer?.();
            if(rootFiles){
              // переносим ВСЕ файлы текущей папки и подпапок
              const files = Array.from(node.querySelectorAll('.mz-tree-file'));
              files.forEach(fileEl=>{
                fileEl.setAttribute('data-folder', '');
                fileEl.dataset.folder = '';

                const tag = fileEl.querySelector('.mz-mat-tag');
                if(tag){
                  tag.textContent = 'Sin módulo';
                  tag.classList.add('muted');
                }

                rootFiles.appendChild(fileEl);
              });
            }
          }

          node.remove();
          window.mzMaterialsSyncCardsFromTree?.();
          window.mzCleanupEmptyPlaceholders?.();
          window.mzMaterialsReindexSearch?.();
          return;
        }

        alert('No se pudo completar: ' + (rr.j.error || rr.j.message || rr.r.status));
        return;
      }

      alert('No se pudo eliminar la carpeta: ' + (res.j.error || res.r.status));
    } catch (err) {
      console.error('[folder-delete] failed', err);
      alert('Error al eliminar la carpeta.');
    }
  });
})();

document.addEventListener('click', async (e)=>{
  const btn = e.target.closest('[data-action="folder.upload.here"]');
  if(!btn) return;
  e.preventDefault();

  const targetPath = (btn.getAttribute('data-parent') || '').trim();

  const inp = document.createElement('input');
  inp.type = 'file';
  inp.multiple = true;
  inp.style.display = 'none';
  document.body.appendChild(inp);

  inp.addEventListener('change', async ()=>{
    try{
      const fn = window.mzMaterialsUploadFilesToFolder;
		if(!fn){
		  alert('Upload helper not ready (mzMaterialsUploadFilesToFolder).');
		  return;
		}
		await fn(inp.files, targetPath);
    }catch(err){
      console.error(err);
      alert('No se pudo subir archivos: ' + (err.message || err));
    }finally{
      document.body.removeChild(inp);
    }
  });

  inp.click();
});

document.addEventListener('click', async (e)=>{
  const btn = e.target.closest('[data-action="folder.upload.bundle"]');
  if(!btn) return;
  e.preventDefault();

  const inp = document.createElement('input');
  inp.type = 'file';
  inp.multiple = true;
  inp.setAttribute('webkitdirectory', '');  // важно
  inp.style.display = 'none';
  document.body.appendChild(inp);

  inp.addEventListener('change', async ()=>{
    try{
      await uploadFolderBundle(inp.files);
    }catch(err){
      console.error(err);
      alert('No se pudo subir la carpeta: ' + (err.message || err));
    }finally{
      document.body.removeChild(inp);
    }
  });

  inp.click();
});

async function uploadFolderBundle(fileList){
  const files = Array.from(fileList || []);
  if(!files.length) return;

  const totalBytes = files.reduce((s, f) => s + (f.size || 0), 0);
  const rootFolderName =
    (files[0] && files[0].webkitRelativePath && files[0].webkitRelativePath.split('/')[0]) || 'Carpeta';

  const uploadUrl = mzPostUrl();

  const jobId = mzUploadOverlay.addJob({
    name: rootFolderName,
    meta: `0 / ${mzBytesHuman(totalBytes)} · ${files.length} archivo(s)`
  });

  const fd = new FormData();
  fd.append('action', 'upload_folder_bundle');

  for(const f of files){
    fd.append('files', f, f.name);
    fd.append('paths', f.webkitRelativePath || f.name);
  }

  let result;
  try{
    const uploadUrl = mzPostUrl();

	result = await postFormXHR(uploadUrl, fd, mzCsrfToken(), {
      onProgress: ({ loaded, total, percent }) => {
        const safeTotal = total || totalBytes || 0;
        mzUploadOverlay.setUploading(jobId, {
          percent,
          meta: `${mzBytesHuman(loaded)} / ${mzBytesHuman(safeTotal)} · ${files.length} archivo(s)`
        });
      }
    });
  }catch(err){
    mzUploadOverlay.setError(jobId, err.message || 'No se pudo subir la carpeta');
    throw err;
  }

  const j = result.j || {};
  if(!j.ok){
    mzUploadOverlay.setError(jobId, j.error || 'upload_folder_failed');
    throw new Error(j.error || 'upload_folder_failed');
  }

  mzUploadOverlay.setDone(jobId, {
    meta: `${mzBytesHuman(totalBytes)} · ${files.length} archivo(s)`
  });

  location.reload();
}

(function initFileDeleteAjax(){
  document.addEventListener('submit', async (e)=>{
    const form = e.target.closest('form[data-ajax="file-delete"]');
    if(!form) return;
    e.preventDefault();

    const csrftoken = mzCsrfToken();

    const r = await fetch(window.location.pathname + window.location.search, {
      method:'POST',
      credentials:'include',
      headers: {
	'X-CSRFToken': mzCsrfToken(),
	'X-Requested-With': 'XMLHttpRequest',
	},
      body: new FormData(form)
    });

    const txt = await r.text();
    let j = {};
    try{ j = txt ? JSON.parse(txt) : {}; }catch(_){}

    if(!r.ok || !j.ok){
      alert('No se pudo eliminar el archivo: ' + (j.error || j.message || r.status));
      return;
    }

    // ✅ remove from DOM
    const row = form.closest('.mz-tree-file, .mz-file-row, [data-drag-file]');
    if(row) row.remove();

	const folderPath = (j.folder_path || '').trim();

	// если файл был в папке
	if(folderPath){
	  mzBumpCount(folderPath, -1, 'direct');
	  mzBumpCountCascadeTotal(folderPath, -1);
	}

	// если файл был в Raíz — просто пересинхроним карточки (root-count берётся из DOM)
	window.mzMaterialsSyncCardsFromTree?.();
	mzCleanupEmptyPlaceholders?.();
	window.mzMaterialsReindexSearch?.();
  });
})();

function mzPostUrl(){
  const u = new URL(location.href);

  // гарантируем, что POST всегда идёт на текущую страницу, без мусора
  // и без странных параметров/пробелов
  const clean = new URL(u.pathname, u.origin);
  for (const [k,v] of u.searchParams.entries()){
    clean.searchParams.set(k, (v || '').trim());
  }

  // иногда у тебя tab/прочие улетают — зафиксируем
  if (!clean.searchParams.get('tab')) clean.searchParams.set('tab','materiales');

  return clean.pathname + '?' + clean.searchParams.toString();
}
// -----------------------------
// UI: simple info modal (reusable)
// -----------------------------
function mzShowModal({ title, html, variant='info' }){
  let modal = document.getElementById('mz-info-modal');
  if(!modal){
    modal = document.createElement('div');
    modal.id = 'mz-info-modal';
    modal.className = 'mz-modal';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="mz-modal-card mz-modal-${variant}" role="dialog" aria-modal="true" aria-labelledby="mz-info-title">
        <div class="mz-modal-head">
          <div id="mz-info-title" class="mz-modal-title"></div>
          <button type="button" class="mz-modal-x" data-x aria-label="Cerrar">✕</button>
        </div>
        <div class="mz-modal-body" data-body></div>
        <div class="mz-modal-actions">
          <button type="button" class="mzc-btn" data-ok>Entendido</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const close = ()=>{
      modal.hidden = true;
      document.body.style.overflow = '';
    };

    modal.addEventListener('click', (e)=>{
      if(e.target === modal) close();
      if(e.target.closest('[data-x]')) close();
      if(e.target.closest('[data-ok]')) close();
    });
    document.addEventListener('keydown', (e)=>{
      if(!modal.hidden && e.key === 'Escape') close();
    });
  }

  modal.querySelector('#mz-info-title').textContent = title || 'Información';
  modal.querySelector('[data-body]').innerHTML = html || '';
  modal.hidden = false;
  document.body.style.overflow = 'hidden';

  // focus
  setTimeout(()=> modal.querySelector('[data-ok]')?.focus(), 0);
}

window.mzShowModal = mzShowModal;

// -----------------------------
// Unified "download blocked" stub (used everywhere)
// -----------------------------
function mzDownloadBlocked(reason){
  // одна-единственная заглушка для любых блокировок скачивания
  window.mzShowModal?.({
    title: 'Descarga bloqueada',
    variant: 'info',
    html: `
      <div style="display:flex; gap:12px; align-items:flex-start">
        <div style="font-size:22px">🔒</div>
        <div>
          <div style="font-weight:900; color:#e5e7eb">No puedes descargar materiales</div>
          <div style="margin-top:6px; opacity:.95">
            El profesor ha desactivado la descarga para tu usuario.
            <br><span style="opacity:.85">Si crees que es un error, avisa a tu profesor/a.</span>
          </div>
        </div>
      </div>
    `
  });
}
window.mzDownloadBlocked = mzDownloadBlocked;

// helper: определить “это именно блокировка доступа”
function mzIsDownloadForbidden(j, status){
  const r = (j && (j.reason || j.error || j.code)) ? String(j.reason || j.error || j.code) : '';
  if (status === 403) return true;
  return [
    'forbidden',
    'module_disabled',
    'no_file_access',
    'no_course_access',
    'download_disabled',
    'not_allowed'
  ].includes(r);
}
window.mzIsDownloadForbidden = mzIsDownloadForbidden;


(function initShareToggleAjax(){
  if (window.__MZ_SHARE_TOGGLE__) return;
  window.__MZ_SHARE_TOGGLE__ = true;

  document.addEventListener('submit', async (e)=>{
    const form = e.target.closest('form[data-ajax="share-toggle"]');
    if(!form) return;

    e.preventDefault();

    const csrftoken = mzCsrfToken();

    let r, txt, j = {};
    try{
      r = await fetch(window.location.pathname + window.location.search, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new FormData(form)
      });

      txt = await r.text();
      try { j = txt ? JSON.parse(txt) : {}; } catch(_){}

      if(!r.ok || !j.ok) throw new Error(j.error || j.message || ('HTTP ' + r.status));
    }catch(err){
      console.error(err);
      alert('No se pudo cambiar visibilidad: ' + (err.message || err));
      return;
    }

    const fileId = String(j.file_id || form.dataset.fileId || '').trim();
    const row =
      document.querySelector(`.mz-tree-file[data-file-id="${CSS.escape(fileId)}"]`) ||
      document.querySelector(`.mz-tree-file[data-drag-file="${CSS.escape(fileId)}"]`);

    if(!row) return;

    // ✅ 1) обновляем "Visible para alumnos" плашку
    const want = !!j.share_alumnos;
	// ✅ 3) обновляем mz-mat-tag (module_key) туда-обратно
	if (j.module_key !== undefined){
	  const tag = row.querySelector('.mz-mat-tag, .mz-tree-modtag');
	  const mk = (j.module_key || '').trim();

	  if(tag){
		tag.textContent = mk ? mk : 'Sin módulo';
		tag.classList.toggle('muted', !mk);
	  }
	}
    let chip = row.querySelector('.mz-file-meta .mz-chip-mini[data-share-chip]');
    if(!chip && want){
      chip = document.createElement('span');
      chip.className = 'mz-chip-mini';
      chip.setAttribute('data-share-chip','1');
      chip.textContent = 'Visible para alumnos';
      row.querySelector('.mz-file-meta')?.appendChild(chip);
    }
    if(chip){
      if(want){
        chip.textContent = 'Visible para alumnos';
        chip.hidden = false;
      }else{
        chip.remove(); // проще убрать полностью
      }
    }

	// ✅ 4) обновляем кнопку (mobile icon OR desktop text)
	const btn = form.querySelector('button[type="submit"]');
	if(btn){
	  const isIcon = (btn.textContent || '').includes('🙈') || (btn.textContent || '').includes('👥');

	  if(isIcon){
		btn.textContent = want ? '🙈' : '👥';
	  }else{
		btn.textContent = want ? 'Ocultar de alumnos' : 'Mostrar a alumnos';
	  }

	  btn.title = want ? 'Ocultar de alumnos' : 'Mostrar a alumnos';
	  btn.setAttribute('aria-label', want ? 'Ocultar de alumnos' : 'Mostrar a alumnos');
	}

    // ✅ ВАЖНО: НИЧЕГО НЕ УДАЛЯЕМ И НЕ ПЕРЕНОСИМ
    // максимум — пересинхроним карточки/поиск
    window.mzMaterialsSyncCardsFromTree?.();
    window.mzMaterialsReindexSearch?.();
  });
})();

(function initMaterialsClear(){
  if (window.__MZ_MATERIALS_CLEAR__) return;
  window.__MZ_MATERIALS_CLEAR__ = true;

  async function postClear(mode, audience){
    const fd = new FormData();
    fd.append('action', 'materials_clear');
    fd.append('mode', mode);           // current | all
    fd.append('audience', audience);   // alumnos | docentes | mis

    const r = await fetch(window.location.pathname + window.location.search, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': mzCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: fd
    });

    const txt = await r.text();
    let j = {};
    try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}

    if(!r.ok || !j.ok){
      throw new Error(j.error || j.message || ('HTTP ' + r.status));
    }
    return j;
  }

  document.addEventListener('click', async (e)=>{
    const btn = e.target.closest('[data-action="materials.clear.ask"]');
    if(!btn) return;

    e.preventDefault();

    const audience = (btn.getAttribute('data-aud') || 'alumnos').trim();

    const choice = await mzConfirmFolderDelete({
      title: 'Vaciar materiales',
      html: `
        <div style="line-height:1.4">
          Puedes limpiar solo esta pestaña o vaciar todos los materiales del curso.
          <div style="margin-top:10px; color:#fca5a5; font-weight:700">
            Esta acción no se puede deshacer.
          </div>
        </div>
      `,
      actions: [
        { label:'Cancelar', value:null },
        { label:'Solo esta pestaña', value:'current' },
        { label:'Todo el curso', value:'all', cls:'danger' },
      ]
    });

    if(!choice) return;

    const confirm2 = await mzConfirmFolderDelete({
      title: 'Confirmación final',
      html: `
        <div style="line-height:1.4">
          ${choice === 'all'
            ? 'Se eliminarán todos los archivos del curso y se quitarán las carpetas personalizadas.'
            : 'Se eliminarán los archivos de esta pestaña actual.'}
          <div style="margin-top:10px; color:#fca5a5; font-weight:700">
            Los archivos físicos en el storage no se borrarán, pero dejarán de estar enlazados.
          </div>
        </div>
      `,
      actions: [
        { label:'Cancelar', value:null },
        { label:'Sí, vaciar', value:'yes', cls:'danger' },
      ]
    });

    if(confirm2 !== 'yes') return;

    const old = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Vaciando...';

    try{
      await postClear(choice, audience);
      location.reload();
    }catch(err){
      console.error(err);
      alert('No se pudo vaciar materiales: ' + (err.message || err));
      btn.disabled = false;
      btn.textContent = old;
    }
  });
})();