/* static/panel/js/materiales_fs.js */
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
      a.href = `?tab=materiales&aud=${aud}&p=${encodeURIComponent(acc)}&mod=${mod}&sort=${sort}`;
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
    root.addEventListener('click', (e)=>{
      const btn = e.target.closest('[data-toggle]');
      if(!btn) return;

      const nodeEl = btn.closest('.mz-tree-node');
      if(!nodeEl) return;

      const kids = nodeEl.querySelector('.mz-tree-children');
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
  // 5) Drag & Drop move file (teacher)
  // -----------------------------
  (function initDnDMove(){
    // “teacher mode” — если есть хоть один data-drop-folder
    const isTeacher = !!document.querySelector('[data-drop-folder]');
    if(!isTeacher) return;

    const csrftoken = getCookie('csrftoken');

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

      const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(targetPath)}"]`);
      if (!node) return null;

      const kids = node.querySelector('.mz-tree-children');
      if (!kids) return null;

      // auto expand
      kids.hidden = false;
      const tgl = node.querySelector('[data-toggle]');
      if (tgl) tgl.textContent = '▾';

      return kids;
    }

    function bumpCount(path, delta){
      if (!path) return;
      const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(path)}"]`);
      if (!node) return;
      const c = node.querySelector('.mz-tree-count');
      if (!c) return;
      const n = parseInt((c.textContent || '0'), 10) || 0;
      c.textContent = String(Math.max(0, n + delta));
    }

    document.addEventListener('dragstart', (e)=>{
      const it = e.target.closest('[data-drag-file]');
      if(!it) return;

      dragEl = it;
      dragFileId = it.getAttribute('data-drag-file');

      if (!isValidNumericId(dragFileId)){
        dragEl = null;
        dragFileId = null;
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
          if(!dragFileId) return;
          folderEl.classList.add('is-drop-ok');
        });

        folderEl.addEventListener('dragover', (e)=>{
          e.preventDefault();
          if(!dragFileId) return;
          e.dataTransfer.dropEffect = 'move';
        });

        folderEl.addEventListener('dragleave', ()=>{
          folderEl.classList.remove('is-drop-ok','is-drop-bad');
        });

        folderEl.addEventListener('drop', async (e)=>{
          e.preventDefault();
          folderEl.classList.remove('is-drop-ok','is-drop-bad');

          const rawId =
            dragFileId ||
            e.dataTransfer.getData('application/x-mz-file-id') ||
            e.dataTransfer.getData('text/plain');

          if(!isValidNumericId(rawId)){
            console.warn('DROP ignored: not a file id', rawId);
            return;
          }
          const fileId = String(rawId).trim();
          const targetPath = folderEl.getAttribute('data-drop-folder') || '';

          let fileEl = document.querySelector(`[data-drag-file="${CSS.escape(fileId)}"]`);
          if(!fileEl){
            console.warn('file element not found for', fileId);
            return;
          }

          const srcNode = fileEl.closest('.mz-tree-node');
          const srcPath = srcNode ? (srcNode.getAttribute('data-node') || '') : '';

          const form = new FormData();
          form.append('action', 'file_move');
          form.append('file_id', fileId);
          form.append('target_path', targetPath);

          try{
            const r = await fetch(window.location.pathname + window.location.search, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'X-CSRFToken': csrftoken,
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
              targetContainer.prepend(fileEl);
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

            if (srcPath !== targetPath){
              if (srcPath) bumpCount(srcPath, -1);
              if (targetPath) bumpCount(targetPath, +1);
            }

          }catch(err){
            console.error(err);
            alert('No se pudo mover el archivo: ' + (err.message || err));
          }
        });
      });
    }

    bindDropTargets();

    // если ты динамически вставляешь новые узлы дерева (folder_create → node_html),
    // можно дернуть повторный bind
    window.mzMaterialsFsBindDropTargets = bindDropTargets;
  })();


  // -----------------------------
  // 6) Create folder (AJAX)
  // -----------------------------
  (function initCreateFolder(){
    const btn = document.querySelector('[data-action="folder.create.big"]');
    const form = document.getElementById('mz-folder-create-form');
    if(!btn || !form) return;

    async function createFolderAjax(name){
      const bc = document.getElementById('mz-fold-bc');
      const parent = bc ? (bc.getAttribute('data-path') || '') : (form.querySelector('[name="folder_parent"]').value || '');
      form.querySelector('[name="folder_parent"]').value = parent;

      const fd = new FormData(form);
      fd.set('folder_name', name);

      const r = await fetch(window.location.pathname + window.location.search, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: fd
      });

      const txt = await r.text();
      let j = {};
      try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
      if(!r.ok || !j.ok) throw new Error(j.error || ('HTTP ' + r.status));
      return j;
    }

    btn.addEventListener('click', async ()=>{
      const name = prompt('Nombre de la carpeta:');
      if(!name) return;

      try{
        const j = await createFolderAjax(name.trim());

        // если backend вернёт готовую верстку узла — вставим
        if (j.node_html){
          const tree = document.querySelector('.mz-tree');
          if (tree) tree.insertAdjacentHTML('afterbegin', j.node_html);

          // важно: если вставили новые drop targets — перебиндить
          if (window.mzMaterialsFsBindDropTargets) window.mzMaterialsFsBindDropTargets();
        } else {
          console.warn('folder created but no node_html returned');
          // fallback: reload (ты можешь убрать, если строго без reload)
          // location.reload();
        }

      }catch(err){
        console.warn('AJAX folder_create failed, fallback to normal submit', err);

        form.querySelector('input[name="folder_name"]').value = name.trim();
        const bc = document.getElementById('mz-fold-bc');
        form.querySelector('[name="folder_parent"]').value = bc ? (bc.getAttribute('data-path') || '') : '';
        form.submit();
      }
    });
  })();


  // -----------------------------
  // 7) Tree sort (folders + files) without reload
  // -----------------------------
  (function initTreeSort(){
    const sortBar = document.querySelector('.mz-mat-sort');
    if(!sortBar) return;

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
      const getLockedKey = (el)=> (el.getAttribute('data-locked') === '1' ? 0 : 1);

      const byName = (a,b)=> getName(a).localeCompare(getName(b), undefined, {numeric:true, sensitivity:'base'});
      const cmp = (a,b)=>{
        const la = getLockedKey(a), lb = getLockedKey(b);
        if (la !== lb) return la - lb; // locked first
        return (mode === 'za') ? -byName(a,b) : byName(a,b);
      };

      nodes.sort(cmp);
      nodes.forEach(n=>container.appendChild(n));
    }

    function applySort(mode){
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