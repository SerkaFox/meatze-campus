/* static/panel/js/materiales_explorer.js */
(() => {
  'use strict';
  if (window.__MZ_MATERIALES_EXPLORER__) return;
  window.__MZ_MATERIALES_EXPLORER__ = true;

  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const selected = new Set();
  const PATH_KEY = 'mz_materiales_explorer_path_v1';
  const VIEW_KEY = 'mz_materiales_explorer_view_v1';
  const SORT_KEY = 'mz_materiales_explorer_sort_v1';
  let clipboard = null;
  let lastClicked = null;
  let contextTarget = null;
  let explorerPath = '';
  let explorerView = 'large';
  let explorerSort = 'name-asc';

  function cursoCodigo(){
    return window.__MZ_CURSO_CODIGO__ || window.mzGetCursoCodigo?.() || '';
  }

  function fsOpUrl(){
    return `/alumno/curso/${encodeURIComponent(cursoCodigo())}/materiales/fs/op/`;
  }

  function folderMoveUrl(){
    return `/alumno/curso/${encodeURIComponent(cursoCodigo())}/materiales/fs/move-folder/`;
  }

  function normPath(p){
    return (p || '').trim().replace(/^\/+|\/+$/g, '');
  }

  function isTypingTarget(el){
    return !!el?.closest?.('input, textarea, select, [contenteditable="true"]');
  }

  function isActionTarget(el){
    return !!el?.closest?.('a, button, input, textarea, select, form, .mz-tree-actions, .mz-file-actions, .mz-drag-handle, [data-toggle], [data-action]');
  }

  function itemFromElement(el){
    const file = el?.closest?.('.mz-tree-file[data-file-id], .mz-tree-file[data-drag-file]');
    if(file){
      const id = file.getAttribute('data-file-id') || file.getAttribute('data-drag-file') || '';
      return { kind:'file', id:String(id), el:file };
    }

    const folderRow = el?.closest?.('.mz-tree-row');
    const node = folderRow?.closest?.('.mz-tree-node[data-node]');
    if(node && folderRow === node.querySelector(':scope > .mz-tree-row')){
      return { kind:'folder', path:normPath(node.getAttribute('data-node')), el:node };
    }

    return null;
  }

  function keyOf(item){
    return item.kind === 'file' ? `file:${item.id}` : `folder:${item.path}`;
  }

  function itemFromKey(key){
    if(key.startsWith('file:')){
      const id = key.slice(5);
      const el =
        $(`#mz-explorer-content .mz-tree-file[data-file-id="${CSS.escape(id)}"]`) ||
        $(`#mz-explorer-content .mz-tree-file[data-drag-file="${CSS.escape(id)}"]`) ||
        $(`.mz-tree-file[data-file-id="${CSS.escape(id)}"]`) ||
        $(`.mz-tree-file[data-drag-file="${CSS.escape(id)}"]`);
      return el ? { kind:'file', id, el } : null;
    }
    if(key.startsWith('folder:')){
      const path = key.slice(7);
      const el =
        $(`#mz-explorer-content .mz-tree-node[data-node="${CSS.escape(path)}"]`) ||
        $(`.mz-tree-node[data-node="${CSS.escape(path)}"]`);
      return el ? { kind:'folder', path, el } : null;
    }
    return null;
  }

  function selectedItems(){
    return Array.from(selected).map(itemFromKey).filter(Boolean);
  }

  function clearSelection(){
    selected.clear();
    $$('.is-selected').forEach(el => el.classList.remove('is-selected'));
    updateToolbar();
  }

  function applySelection(){
    $$('.is-selected').forEach(el => el.classList.remove('is-selected'));
    selectedItems().forEach(item => item.el.classList.add('is-selected'));
    updateToolbar();
  }

  function selectOnly(item){
    selected.clear();
    selected.add(keyOf(item));
    lastClicked = item;
    applySelection();
  }

  function toggleSelection(item){
    const key = keyOf(item);
    if(selected.has(key)) selected.delete(key);
    else selected.add(key);
    lastClicked = item;
    applySelection();
  }

  function rangeSelect(item){
    const all = $$('.mz-tree-file[data-file-id], .mz-tree-file[data-drag-file], .mz-tree-node[data-node]');
    const a = lastClicked ? all.indexOf(lastClicked.el) : -1;
    const b = all.indexOf(item.el);
    if(a < 0 || b < 0){
      selectOnly(item);
      return;
    }
    const from = Math.min(a, b);
    const to = Math.max(a, b);
    selected.clear();
    all.slice(from, to + 1).forEach(el => {
      const it = itemFromElement(el);
      if(it) selected.add(keyOf(it));
    });
    applySelection();
  }

  function updateToolbar(){
    const count = selectedItems().length;
    const status = $('[data-explorer-status]');
    if(status) status.textContent = `${count} seleccionado${count === 1 ? '' : 's'}`;

    $$('[data-explorer-action]').forEach(btn => {
      const action = btn.getAttribute('data-explorer-action');
      const needsSelection = ['cut', 'copy', 'rename', 'delete', 'access'].includes(action);
      const needsSingle = ['rename', 'access'].includes(action);
      const needsClipboard = action === 'paste';
      btn.disabled =
        (needsSelection && count === 0) ||
        (needsSingle && count !== 1) ||
        (needsClipboard && !clipboard?.items?.length);
    });

    $$('.is-cutting').forEach(el => el.classList.remove('is-cutting'));
    if(clipboard?.mode === 'cut'){
      clipboard.items.forEach(item => {
        const current = item.kind === 'file'
          ? itemFromKey(`file:${item.id}`)
          : itemFromKey(`folder:${item.path}`);
        current?.el?.classList.add('is-cutting');
      });
    }
  }

  async function postJSON(url, payload){
    const r = await fetch(url, {
      method:'POST',
      credentials:'include',
      headers:{
        'Content-Type':'application/json',
        'X-CSRFToken': window.mzCsrfToken?.() || '',
        'X-Requested-With':'XMLHttpRequest',
      },
      body: JSON.stringify(payload || {}),
    });
    const txt = await r.text();
    let j = {};
    try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
    if(!r.ok || !j.ok) throw new Error(j.error || j.message || txt || `HTTP ${r.status}`);
    return j;
  }

  async function postForm(payload){
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => fd.append(k, v == null ? '' : String(v)));

    const r = await fetch(window.mzPostUrl?.() || (location.pathname + location.search), {
      method:'POST',
      credentials:'include',
      headers:{
        'X-CSRFToken': window.mzCsrfToken?.() || '',
        'X-Requested-With':'XMLHttpRequest',
      },
      body: fd,
    });
    const txt = await r.text();
    let j = {};
    try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
    if(!r.ok || !j.ok) throw new Error(j.error || j.message || txt || `HTTP ${r.status}`);
    return j;
  }

  async function postFormRaw(payload){
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => fd.append(k, v == null ? '' : String(v)));

    const r = await fetch(window.mzPostUrl?.() || (location.pathname + location.search), {
      method:'POST',
      credentials:'include',
      headers:{
        'X-CSRFToken': window.mzCsrfToken?.() || '',
        'X-Requested-With':'XMLHttpRequest',
      },
      body: fd,
    });
    const txt = await r.text();
    let j = {};
    try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
    return { r, j, txt };
  }

  function currentFolderPath(){
    if(!$('#mz-explorer-wrap')?.hidden) return normPath(explorerPath);
    if(window.__MZ_CARDS_MOUNT_PATH__ != null) return normPath(window.__MZ_CARDS_MOUNT_PATH__);
    const bc = $('#mz-fold-bc');
    return normPath(bc?.getAttribute('data-path') || '');
  }

  function targetFolderFromEvent(el){
    const drop = el?.closest?.('[data-drop-folder]');
    if(drop && drop.hasAttribute('data-drop-folder')){
      return normPath(drop.getAttribute('data-drop-folder'));
    }

    const item = itemFromElement(el);
    if(item?.kind === 'folder') return item.path;
    return currentFolderPath();
  }

  function targetFolderForPaste(){
    if(contextTarget) return targetFolderFromEvent(contextTarget.el || contextTarget);
    return currentFolderPath();
  }

  function selectedZipFile(){
    const item = selectedItems()[0];
    if(!item || item.kind !== 'file') return null;
    const name = (
      item.el.getAttribute('data-name') ||
      item.el.querySelector('.mz-file-name')?.textContent ||
      ''
    ).trim().toLowerCase();
    const ext = name.split('.').pop();
    return ext === 'zip' ? item : null;
  }

  async function renameSelected(){
    const item = selectedItems()[0];
    if(!item) return;

    const currentName = item.kind === 'file'
      ? (item.el.getAttribute('data-name') || item.el.querySelector('.mz-file-name')?.textContent || '').trim()
      : (item.el.getAttribute('data-folder-name') || item.path.split('/').pop() || '').trim();
    const name = prompt('Nuevo nombre:', currentName);
    if(!name || name.trim() === currentName) return;

    try{
      if(item.kind === 'file'){
        const j = await postJSON(fsOpUrl(), {
          op:'rename_file',
          file_id:item.id,
          name:name.trim(),
          audience: window.__MZ_AUD__ || 'alumnos',
        });
        item.el.setAttribute('data-name', j.name || name.trim());
        const nameEl = item.el.querySelector('.mz-file-name');
        if(nameEl) nameEl.textContent = j.name || name.trim();
        window.mzMaterialsReindexSearch?.();
      }else{
        await postJSON(fsOpUrl(), {
          op:'rename_folder',
          source_path:item.path,
          name:name.trim(),
          audience: window.__MZ_AUD__ || 'alumnos',
        });
        location.reload();
      }
    }catch(err){
      alert('No se pudo cambiar el nombre: ' + (err.message || err));
    }
  }

  function setClipboard(mode){
    const items = selectedItems().map(item => (
      item.kind === 'file'
        ? { kind:'file', id:item.id }
        : { kind:'folder', path:item.path }
    ));
    if(!items.length) return;
    clipboard = { mode, items };
    updateToolbar();
  }

  async function moveFile(fileId, targetPath){
    return postForm({
      action:'file_move',
      file_id:fileId,
      target_path:targetPath,
    });
  }

  async function moveFolder(path, targetParent){
    return postJSON(folderMoveUrl(), {
      source_path:path,
      target_parent:targetParent,
    });
  }

  function sourceTree(){
    return $('#mz-tree-wrap .mz-tree');
  }

  function descendantStats(path){
    const p = normPath(path);
    if(!p){
      return {
        folders: allSourceFolders().length,
        files: Array.from(document.querySelectorAll('#mz-tree-wrap .mz-tree-file')).length,
      };
    }

    const node = sourceFolderNode(p);
    if(!node) return { folders:0, files:0 };
    return {
      folders: node.querySelectorAll('.mz-tree-node[data-node]').length,
      files: node.querySelectorAll('.mz-tree-file').length,
    };
  }

  function sourceFolderNode(path){
    const tree = sourceTree();
    if(!tree) return null;
    return tree.querySelector(`.mz-tree-node[data-node="${CSS.escape(normPath(path))}"]`);
  }

  function directContainer(path){
    const tree = sourceTree();
    const p = normPath(path);
    if(!tree) return null;
    if(!p) return tree;
    const node = sourceFolderNode(p);
    return node ? node.querySelector(':scope > .mz-tree-children') : null;
  }

  function ensureSourceChildren(path){
    const tree = sourceTree();
    const p = normPath(path);
    if(!tree) return null;

    if(!p){
      let root = tree.querySelector(':scope > .mz-tree-rootfolders');
      if(!root){
        root = document.createElement('div');
        root.className = 'mz-tree-rootfolders';
        const rootFiles = tree.querySelector(':scope > .mz-tree-rootfiles');
        if(rootFiles) tree.insertBefore(root, rootFiles);
        else tree.prepend(root);
      }
      return root;
    }

    const node = sourceFolderNode(p);
    if(!node) return null;

    let kids = node.querySelector(':scope > .mz-tree-children');
    if(!kids){
      kids = document.createElement('div');
      kids.className = 'mz-tree-children';
      node.appendChild(kids);
    }
    return kids;
  }

  function directFolders(path){
    const p = normPath(path);
    const container = directContainer(p);
    if(!container) return [];

    if(!p){
      const rootNodes = Array.from(container.querySelectorAll(':scope > .mz-tree-node[data-node]'));
      const rootWrapped = Array.from(container.querySelectorAll(':scope > .mz-tree-rootfolders > .mz-tree-node[data-node]'));
      return rootNodes.concat(rootWrapped);
    }
    return Array.from(container.querySelectorAll(':scope > .mz-tree-node[data-node]'));
  }

  function directFiles(path){
    const p = normPath(path);
    if(!p){
      return Array.from(document.querySelectorAll('#mz-tree-wrap .mz-tree-rootfiles > .mz-tree-file'));
    }
    const container = directContainer(p);
    return container ? Array.from(container.querySelectorAll(':scope > .mz-tree-file')) : [];
  }

  function allSourceFolders(){
    const tree = sourceTree();
    return tree ? Array.from(tree.querySelectorAll('.mz-tree-node[data-node]')) : [];
  }

  function folderDepth(path){
    const p = normPath(path);
    return p ? p.split('/').length : 0;
  }

  function cloneFolderRow(node){
    const clone = node.cloneNode(true);
    clone.querySelector(':scope > .mz-tree-children')?.remove();
    clone.classList.remove('is-selected', 'is-cutting');
    clone.querySelectorAll('script').forEach(s => s.remove());
    clone.setAttribute('draggable', 'true');
    clone.setAttribute('data-explorer-kind', 'folder');

    const row = clone.querySelector(':scope > .mz-tree-row');
    if(row){
      row.setAttribute('data-drop-folder', normPath(clone.getAttribute('data-node')));
      row.setAttribute('title', 'Doble clic para abrir');
    }
    decorateExplorerItem(clone);
    return clone;
  }

  function cloneFileRow(file){
    const clone = file.cloneNode(true);
    clone.classList.remove('is-selected', 'is-cutting', 'is-dragging');
    clone.setAttribute('draggable', 'true');
    clone.setAttribute('data-explorer-kind', 'file');
    clone.querySelectorAll('script').forEach(s => s.remove());
    decorateExplorerItem(clone);
    return clone;
  }

  function decorateExplorerItem(el){
    el.querySelectorAll(':scope .mz-explorer-thumb, :scope .mz-explorer-table-date, :scope .mz-explorer-table-size').forEach(x => x.remove());

    const thumb = document.createElement('div');
    thumb.className = 'mz-explorer-thumb';

    if(el.matches('.mz-tree-node')){
      thumb.textContent = '📁';
      el.querySelector(':scope > .mz-tree-row')?.prepend(thumb);
    }else{
      const ext = (el.getAttribute('data-ext') || '').toLowerCase();
      const previewUrl = el.querySelector('a[data-preview]')?.getAttribute('href') || '';
      if(['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext) && previewUrl){
        const img = document.createElement('img');
        img.src = previewUrl;
        img.alt = '';
        img.loading = 'lazy';
        thumb.appendChild(img);
      }else{
        thumb.textContent = fileIcon(ext);
        thumb.setAttribute('data-ext', ext ? ext.toUpperCase() : 'FILE');
      }
      el.prepend(thumb);
    }

    const date = document.createElement('div');
    date.className = 'mz-explorer-table-date';
    date.textContent = formatDate(itemTime(el));

    const size = document.createElement('div');
    size.className = 'mz-explorer-table-size';
    size.textContent = el.matches('.mz-tree-file')
      ? formatBytes(itemSize(el))
      : `${itemSize(el)} archivos`;

    if(el.matches('.mz-tree-node')){
      const row = el.querySelector(':scope > .mz-tree-row');
      row?.appendChild(date);
      row?.appendChild(size);
    }else{
      el.appendChild(date);
      el.appendChild(size);
    }
  }

  function fileIcon(ext){
    if(ext === 'pdf') return 'PDF';
    if(['doc', 'docx', 'odt'].includes(ext)) return 'DOC';
    if(['xls', 'xlsx', 'ods', 'csv'].includes(ext)) return 'XLS';
    if(['ppt', 'pptx', 'odp'].includes(ext)) return 'PPT';
    if(['zip', 'rar', '7z'].includes(ext)) return 'ZIP';
    if(['mp4', 'mov', 'avi', 'webm'].includes(ext)) return 'VID';
    if(['mp3', 'wav', 'ogg'].includes(ext)) return 'AUD';
    if(['txt', 'md'].includes(ext)) return 'TXT';
    return ext ? ext.slice(0, 4).toUpperCase() : 'FILE';
  }

  function formatBytes(n){
    if(window.mzBytesHuman) return window.mzBytesHuman(n);
    const num = Number(n || 0);
    if(num < 1024) return `${num} B`;
    if(num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
    if(num < 1024 * 1024 * 1024) return `${(num / 1024 / 1024).toFixed(1)} MB`;
    return `${(num / 1024 / 1024 / 1024).toFixed(1)} GB`;
  }

  function formatDate(ts){
    const n = Number(ts || 0);
    if(!n) return '—';
    try{
      return new Intl.DateTimeFormat(undefined, {
        day:'2-digit',
        month:'2-digit',
        year:'2-digit',
        hour:'2-digit',
        minute:'2-digit',
      }).format(new Date(n * 1000));
    }catch(_){
      return '—';
    }
  }

  function itemName(el){
    if(el.matches('.mz-tree-file')){
      return (el.getAttribute('data-name') || '').trim().toLowerCase();
    }
    return (el.getAttribute('data-folder-name') || '').trim().toLowerCase();
  }

  function itemTime(el){
    if(el.matches('.mz-tree-file')){
      return parseInt(el.getAttribute('data-ts') || '0', 10) || 0;
    }
    const path = normPath(el.getAttribute('data-node'));
    const src = sourceFolderNode(path);
    const times = src ? Array.from(src.querySelectorAll('.mz-tree-file[data-ts]')).map(f => parseInt(f.getAttribute('data-ts') || '0', 10) || 0) : [];
    return times.length ? Math.max(...times) : 0;
  }

  function itemSize(el){
    if(el.matches('.mz-tree-file')){
      return parseInt(el.getAttribute('data-size') || '0', 10) || 0;
    }
    const path = normPath(el.getAttribute('data-node'));
    const src = sourceFolderNode(path);
    return src ? src.querySelectorAll('.mz-tree-file').length : 0;
  }

  function sortExplorerItems(items){
    const foldersFirst = (a, b) => {
      const af = a.matches('.mz-tree-node') ? 0 : 1;
      const bf = b.matches('.mz-tree-node') ? 0 : 1;
      return af - bf;
    };

    const byName = (a, b) => itemName(a).localeCompare(itemName(b), undefined, { numeric:true, sensitivity:'base' });
    const byTime = (a, b) => itemTime(a) - itemTime(b);
    const bySize = (a, b) => itemSize(a) - itemSize(b);

    const cmp = (a, b) => {
      const ff = foldersFirst(a, b);
      if(ff) return ff;
      if(explorerSort === 'time-desc') return byTime(b, a) || byName(a, b);
      if(explorerSort === 'time-asc') return byTime(a, b) || byName(a, b);
      if(explorerSort === 'size-desc') return bySize(b, a) || byName(a, b);
      if(explorerSort === 'size-asc') return bySize(a, b) || byName(a, b);
      return byName(a, b);
    };

    return items.sort(cmp);
  }

  function applyExplorerView(){
    const content = $('#mz-explorer-content');
    if(!content) return;
    content.classList.toggle('is-large-view', explorerView === 'large');
    content.classList.toggle('is-table-view', explorerView === 'table');
    $$('[data-explorer-view]').forEach(btn => {
      btn.classList.toggle('is-active', btn.getAttribute('data-explorer-view') === explorerView);
    });
    const sort = $('#mz-explorer-sort');
    if(sort) sort.value = explorerSort;
  }

  function buildExplorerNav(){
    const nav = $('#mz-explorer-nav');
    if(!nav) return;

    const folders = allSourceFolders().sort((a, b) => {
      const ap = normPath(a.getAttribute('data-node'));
      const bp = normPath(b.getAttribute('data-node'));
      return ap.localeCompare(bp, undefined, { numeric:true, sensitivity:'base' });
    });

    nav.innerHTML = '';

    const root = document.createElement('button');
    root.type = 'button';
    root.className = 'mz-explorer-nav-item';
    root.setAttribute('data-explorer-open', '');
    root.setAttribute('data-drop-folder', '');
    const rootStats = descendantStats('');
    root.innerHTML = '<span>🏠</span><span class="mz-explorer-nav-name">Raíz</span><span class="mz-explorer-nav-count"></span>';
    root.querySelector('.mz-explorer-nav-count').textContent = `📁${rootStats.folders} 📄${rootStats.files}`;
    nav.appendChild(root);

    folders.forEach(node => {
      const path = normPath(node.getAttribute('data-node'));
      const name = (node.getAttribute('data-folder-name') || path.split('/').pop() || path).trim();
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mz-explorer-nav-item';
      btn.setAttribute('data-explorer-open', path);
      btn.setAttribute('data-drop-folder', path);
      btn.style.paddingLeft = `${7 + Math.min(folderDepth(path), 8) * 14}px`;
      const stats = descendantStats(path);
      btn.innerHTML = `<span>📁</span><span class="mz-explorer-nav-name"></span><span class="mz-explorer-nav-count"></span>`;
      btn.querySelector('.mz-explorer-nav-name').textContent = name;
      btn.querySelector('.mz-explorer-nav-count').textContent = `📁${stats.folders} 📄${stats.files}`;
      nav.appendChild(btn);
    });
  }

  function setExplorerPath(path){
    explorerPath = normPath(path);
    const content = $('#mz-explorer-content');
    const label = $('#mz-explorer-path');
    const summary = $('#mz-explorer-summary');
    if(!content || !label) return;

    content.setAttribute('data-drop-folder', explorerPath);
    label.textContent = explorerPath || 'Raíz';
    if(summary) summary.textContent = '0 carpetas · 0 archivos';
    content.innerHTML = '';

    if(explorerPath && !sourceFolderNode(explorerPath)){
      explorerPath = '';
      content.setAttribute('data-drop-folder', '');
      label.textContent = 'Raíz';
    }

    const folders = directFolders(explorerPath);
    const files = directFiles(explorerPath);
    if(summary) {
      const deep = descendantStats(explorerPath);
      summary.textContent = `${folders.length} carpetas · ${files.length} archivos directos · total: ${deep.folders} carpetas / ${deep.files} archivos`;
    }

    const items = folders.map(cloneFolderRow).concat(files.map(cloneFileRow));
    sortExplorerItems(items).forEach(el => content.appendChild(el));

    if(!folders.length && !files.length){
      const empty = document.createElement('div');
      empty.className = 'mz-explorer-empty';
      empty.textContent = 'Carpeta vacía';
      content.appendChild(empty);
    }

    $$('.mz-explorer-nav-item').forEach(btn => {
      btn.classList.toggle('is-active', normPath(btn.getAttribute('data-explorer-open')) === explorerPath);
    });

    clearSelection();
    try { localStorage.setItem(PATH_KEY, explorerPath); } catch(_) {}
    applyExplorerView();
    window.mzMaterialsFsBindDropTargets?.();
  }

  function refreshExplorer(){
    buildExplorerNav();
    setExplorerPath(explorerPath);
  }

  window.mzMaterialsExplorerRefresh = refreshExplorer;
  window.mzMaterialsExplorerOpenFile = (fileId, folderPath) => {
    setExplorerPath(folderPath || '');
    setTimeout(() => {
      const id = String(fileId || '');
      const el =
        $(`#mz-explorer-content .mz-tree-file[data-file-id="${CSS.escape(id)}"]`) ||
        $(`#mz-explorer-content .mz-tree-file[data-drag-file="${CSS.escape(id)}"]`);
      if(!el) return;
      const item = itemFromElement(el);
      if(item) selectOnly(item);
      el.classList.add('is-found');
      el.scrollIntoView({ behavior:'smooth', block:'center' });
      setTimeout(() => el.classList.remove('is-found'), 1400);
    }, 80);
  };

  async function pasteClipboard(){
    if(!clipboard?.items?.length) return;
    const targetParent = targetFolderForPaste();

    try{
      if(clipboard.mode === 'copy'){
        await postJSON(fsOpUrl(), {
          op:'copy_items',
          target_parent:targetParent,
          audience: window.__MZ_AUD__ || 'alumnos',
          items: clipboard.items,
        });
        try { localStorage.setItem(PATH_KEY, targetParent); } catch(_) {}
        location.reload();
        return;
      }

      for(const item of clipboard.items){
        if(item.kind === 'file') await moveFile(item.id, targetParent);
        if(item.kind === 'folder') await moveFolder(item.path, targetParent);
      }
      clipboard = null;
      try { localStorage.setItem(PATH_KEY, targetParent); } catch(_) {}
      location.reload();
    }catch(err){
      alert('No se pudo pegar: ' + (err.message || err));
    }finally{
      updateToolbar();
    }
  }

  function buildZipUrl(path, scope){
    const base = window.__MZ_ZIP_URL__ || '/panel/materiales/zip/';
    const url = new URL(base, location.origin);
    url.searchParams.set('codigo', cursoCodigo());
    url.searchParams.set('aud', window.__MZ_AUD__ || 'alumnos');
    url.searchParams.set('scope', scope || (path ? 'folder' : 'root'));
    url.searchParams.set('p', normPath(path));
    return url.toString();
  }

  function downloadUrl(url){
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function downloadZipHere(){
    const items = selectedItems();
    const path = (items.length === 1 && items[0].kind === 'folder')
      ? items[0].path
      : targetFolderForPaste();
    downloadUrl(buildZipUrl(path, path ? 'folder' : 'root'));
  }

  async function extractSelectedZip(){
    const item = selectedZipFile();
    if(!item){
      alert('Selecciona un archivo ZIP.');
      return;
    }

    const targetParent = normPath(item.el.getAttribute('data-folder') || currentFolderPath());
    let wrapFolder = false;

    try{
      const info = await postJSON(fsOpUrl(), {
        op:'zip_info',
        file_id:item.id,
      });

      if((info.root_files || 0) > 1){
        const choice = await chooseZipExtractMode(info);
        if(!choice) return;
        wrapFolder = choice === 'folder';
      }else if(!confirm('¿Descomprimir este ZIP en la carpeta actual?')){
        return;
      }
    }catch(err){
      alert('No se pudo leer ZIP: ' + (err.message || err));
      return;
    }

    try{
      await postJSON(fsOpUrl(), {
        op:'extract_zip_file',
        file_id:item.id,
        target_parent:targetParent,
        wrap_folder:wrapFolder,
      });
      try { localStorage.setItem(PATH_KEY, targetParent); } catch(_) {}
      location.reload();
    }catch(err){
      alert('No se pudo descomprimir ZIP: ' + (err.message || err));
    }
  }

  function chooseZipExtractMode(info){
    const archiveName = String(info.archive_name || 'archivo');
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (m) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[m]));

    if(window.mzConfirmFolderDelete){
      return window.mzConfirmFolderDelete({
        title:'Descomprimir ZIP',
        html: `
          <div style="line-height:1.35">
            El ZIP contiene <b>${info.root_files || 0}</b> archivos en la raíz.
            <div class="mz-zip-target-name" title="${esc(archiveName)}">
              Carpeta propuesta: <b>${esc(archiveName)}</b>
            </div>
            <div style="margin-top:8px">¿Dónde quieres descomprimirlos?</div>
          </div>
        `,
        actions:[
          { label:'Cancelar', value:null },
          { label:'Aquí', value:'current' },
          { label:'Crear carpeta', value:'folder' },
        ],
      });
    }

    const ok = confirm('El ZIP tiene varios archivos en la raíz. Aceptar = crear carpeta con el nombre del ZIP. Cancelar = descomprimir en la carpeta actual.');
    return ok ? 'folder' : 'current';
  }

  function openGoogleDriveHere(targetPath = currentFolderPath()){
    const cfg = $('#mz-gdrive-cfg');
    const hasCfg = !!(
      cfg &&
      (cfg.getAttribute('data-client-id') || '').trim() &&
      (cfg.getAttribute('data-api-key') || '').trim() &&
      (cfg.getAttribute('data-app-id') || '').trim()
    );
    if(!hasCfg){
      alert('Google Drive no está configurado en este entorno.');
      return;
    }

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.setAttribute('data-action', 'folder.upload.google');
    btn.setAttribute('data-parent', normPath(targetPath));
    btn.hidden = true;
    document.body.appendChild(btn);
    btn.click();
    btn.remove();
  }

  function accessModal(item){
    let modal = $('#mz-access-modal');
    if(!modal){
      modal = document.createElement('div');
      modal.id = 'mz-access-modal';
      modal.className = 'mz-modal';
      modal.hidden = true;
      modal.innerHTML = `
        <div class="mz-modal-card" role="dialog" aria-modal="true" aria-labelledby="mz-access-title">
          <div class="mz-modal-head">
            <div id="mz-access-title" class="mz-modal-title">Acceso</div>
            <button type="button" class="mz-modal-x" data-x aria-label="Cerrar">✕</button>
          </div>
          <div class="mz-modal-body">
            <div class="mz-access-options">
              <label class="mz-access-row">
                <input type="radio" name="mz_access_tipo" value="alumnos">
                <span><b>Para alumnos</b><small>Visible directamente para estudiantes.</small></span>
              </label>
              <label class="mz-access-row">
                <input type="radio" name="mz_access_tipo" value="docentes">
                <span><b>Para todos los profesores</b><small>Compartido entre docentes del curso.</small></span>
              </label>
              <label class="mz-access-row">
                <input type="radio" name="mz_access_tipo" value="privado">
                <span><b>Solo para mí</b><small>Material privado del profesor actual.</small></span>
              </label>
              <label class="mz-access-row" data-share-row>
                <input type="checkbox" name="mz_access_share">
                <span><b>También visible para alumnos</b><small>Disponible para archivos de profesores o privados.</small></span>
              </label>
              <label class="mz-access-row" data-recursive-row>
                <input type="checkbox" name="mz_access_recursive" checked>
                <span><b>Aplicar a todo el contenido</b><small>Incluye archivos dentro de subcarpetas.</small></span>
              </label>
            </div>
          </div>
          <div class="mz-modal-actions">
            <button type="button" class="mzc-btn ghost" data-cancel>Cancelar</button>
            <button type="button" class="mzc-btn" data-save>Guardar</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    const currentTipo = item.kind === 'file'
      ? (item.el.getAttribute('data-tipo') || window.__MZ_AUD__ || 'alumnos')
      : (window.__MZ_AUD__ === 'mis' ? 'privado' : (window.__MZ_AUD__ || 'alumnos'));
    const currentShare = item.kind === 'file'
      ? item.el.getAttribute('data-share-alumnos') === '1'
      : false;

    modal.querySelectorAll('input[name="mz_access_tipo"]').forEach(inp => {
      inp.checked = inp.value === currentTipo;
    });
    const share = modal.querySelector('input[name="mz_access_share"]');
    if(share) share.checked = currentShare;

    const recursiveRow = modal.querySelector('[data-recursive-row]');
    if(recursiveRow) recursiveRow.hidden = item.kind !== 'folder';

    function syncShare(){
      const tipo = modal.querySelector('input[name="mz_access_tipo"]:checked')?.value || 'alumnos';
      const row = modal.querySelector('[data-share-row]');
      if(row) row.hidden = tipo === 'alumnos';
      if(tipo === 'alumnos' && share) share.checked = false;
    }
    syncShare();

    return new Promise(resolve => {
      const close = (value) => {
        modal.hidden = true;
        document.body.style.overflow = '';
        modal.onclick = null;
        modal.querySelector('[data-save]').onclick = null;
        modal.querySelector('[data-cancel]').onclick = null;
        resolve(value);
      };

      modal.querySelectorAll('input[name="mz_access_tipo"]').forEach(inp => {
        inp.onchange = syncShare;
      });
      modal.querySelector('[data-save]').onclick = () => {
        close({
          tipo: modal.querySelector('input[name="mz_access_tipo"]:checked')?.value || 'alumnos',
          share_alumnos: !!modal.querySelector('input[name="mz_access_share"]')?.checked,
          recursive: !!modal.querySelector('input[name="mz_access_recursive"]')?.checked,
        });
      };
      modal.querySelector('[data-cancel]').onclick = () => close(null);
      modal.onclick = (e) => {
        if(e.target === modal || e.target.closest('[data-x]')) close(null);
      };

      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      setTimeout(() => modal.querySelector('[data-save]')?.focus(), 0);
    });
  }

  async function changeAccess(){
    const item = selectedItems()[0];
    if(!item) return;
    const value = await accessModal(item);
    if(!value) return;

    try{
      if(item.kind === 'file'){
        await postJSON(fsOpUrl(), {
          op:'set_file_access',
          file_id:item.id,
          tipo:value.tipo,
          share_alumnos:value.share_alumnos,
        });
      }else{
        await postJSON(fsOpUrl(), {
          op:'set_folder_access',
          path:item.path,
          tipo:value.tipo,
          share_alumnos:value.share_alumnos,
          recursive:value.recursive,
        });
      }
      location.reload();
    }catch(err){
      alert('No se pudo cambiar el acceso: ' + (err.message || err));
    }
  }

  async function uploadHere(targetPath = currentFolderPath()){
    const fn = window.mzMaterialsUploadFilesToFolder;
    if(!fn){
      alert('Upload helper not ready.');
      return;
    }

    const inp = document.createElement('input');
    inp.type = 'file';
    inp.multiple = true;
    inp.style.display = 'none';
    document.body.appendChild(inp);

    inp.addEventListener('change', async () => {
      try{
        await fn(inp.files, normPath(targetPath));
        setTimeout(refreshExplorer, 120);
      }catch(err){
        alert('No se pudo subir archivos: ' + (err.message || err));
      }finally{
        inp.remove();
      }
    });

    inp.click();
  }

  async function uploadFolderHere(targetPath = currentFolderPath()){
    const files = await pickFolderFiles();
    if(!files.length) return;

    const totalBytes = files.reduce((s, f) => s + (f.size || 0), 0);
    const firstPath = files[0]?.webkitRelativePath || files[0]?.name || 'Carpeta';
    const rootFolderName = firstPath.split('/')[0] || 'Carpeta';
    const human = window.mzBytesHuman || ((n) => `${n} B`);

    const jobId = window.mzUploadOverlay?.addJob?.({
      name: rootFolderName,
      meta: `0 / ${human(totalBytes)} · ${files.length} archivo(s)`,
    });

    const fd = new FormData();
    fd.append('action', 'upload_folder_bundle');
    fd.append('target_path', normPath(targetPath));
    fd.append('audience', window.__MZ_AUD__ || 'alumnos');

    files.forEach(file => {
      fd.append('files', file, file.name);
      fd.append('paths', file.webkitRelativePath || file.name);
    });

    try{
      await postFolderForm(fd, {
        onProgress: ({ loaded, total, percent }) => {
          if(!jobId || !window.mzUploadOverlay?.setUploading) return;
          window.mzUploadOverlay.setUploading(jobId, {
            percent,
            meta: `${human(loaded)} / ${human(total || totalBytes)} · ${files.length} archivo(s)`,
          });
        },
      });
      if(jobId) window.mzUploadOverlay?.setDone?.(jobId, {
        meta: `${human(totalBytes)} · ${files.length} archivo(s)`,
      });
      try { localStorage.setItem(PATH_KEY, normPath(targetPath)); } catch(_) {}
      location.reload();
    }catch(err){
      if(jobId) window.mzUploadOverlay?.setError?.(jobId, err.message || 'No se pudo subir la carpeta');
      alert('No se pudo subir la carpeta: ' + (err.message || err));
    }
  }

  function pickFolderFiles(){
    return new Promise(resolve => {
      const inp = document.createElement('input');
      inp.type = 'file';
      inp.multiple = true;
      inp.setAttribute('webkitdirectory', '');
      inp.style.display = 'none';
      document.body.appendChild(inp);
      inp.addEventListener('change', () => {
        const files = Array.from(inp.files || []);
        inp.remove();
        resolve(files);
      }, { once:true });
      inp.click();
    });
  }

  function postFolderForm(formData, { onProgress } = {}){
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', window.mzPostUrl?.() || (location.pathname + location.search), true);
      xhr.withCredentials = true;
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      const csrf = window.mzCsrfToken?.() || '';
      if(csrf) xhr.setRequestHeader('X-CSRFToken', csrf);
      if(xhr.upload && typeof onProgress === 'function'){
        xhr.upload.addEventListener('progress', (ev) => {
          if(!ev.lengthComputable) return;
          onProgress({
            loaded: ev.loaded || 0,
            total: ev.total || 0,
            percent: ev.total ? (ev.loaded / ev.total * 100) : 0,
          });
        });
      }
      xhr.onload = () => {
        const txt = xhr.responseText || '';
        let j = {};
        try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}
        if(xhr.status >= 200 && xhr.status < 300 && j.ok) resolve(j);
        else reject(new Error(j.error || j.message || txt || `HTTP ${xhr.status}`));
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  }

  async function deleteSelected(){
    const items = selectedItems();
    if(!items.length) return;
    if(!confirm(`Eliminar ${items.length} elemento(s)?`)) return;

    try{
      for(const item of items){
        if(item.kind === 'file'){
          const folderPath = item.el.getAttribute('data-folder') || '';
          await postForm({ delete_id:item.id });
          item.el.remove();
          if(folderPath){
            window.mzBumpCount?.(folderPath, -1, 'direct');
            window.mzBumpCountCascadeTotal?.(folderPath, -1);
          }
        }else{
          const checked = await postFormRaw({ action:'folder_delete', path:item.path, mode:'check' });
          if(checked.r.ok && checked.j.ok){
            item.el.remove();
            continue;
          }

          if(checked.r.status !== 409 || checked.j.error !== 'folder_not_empty'){
            throw new Error(checked.j.error || checked.j.message || checked.txt || `HTTP ${checked.r.status}`);
          }

          const files = checked.j.files_count || 0;
          const subs = checked.j.subfolders_count || 0;
          let choice = null;

          if(window.mzConfirmFolderDelete){
            choice = await window.mzConfirmFolderDelete({
              title:'Eliminar carpeta',
              html: `
                <div style="line-height:1.35">
                  La carpeta <b>${item.path}</b> no está vacía.<br>
                  <span>Archivos: <b>${files}</b>, Subcarpetas: <b>${subs}</b></span>
                </div>
              `,
              actions:[
                { label:'Cancelar', value:null },
                { label:'Mover archivos al raíz', value:'move_root' },
                { label:'Eliminar TODO', value:'purge', cls:'danger' },
              ],
            });
          }else{
            choice = confirm(`La carpeta "${item.path}" no está vacía. Aceptar = eliminar todo, Cancelar = no borrar.`) ? 'purge' : null;
          }

          if(!choice) continue;
          const done = await postFormRaw({ action:'folder_delete', path:item.path, mode:choice });
          if(!done.r.ok || !done.j.ok){
            throw new Error(done.j.error || done.j.message || done.txt || `HTTP ${done.r.status}`);
          }
          item.el.remove();
        }
      }
      clearSelection();
      window.mzMaterialsSyncCardsFromTree?.();
      window.mzCleanupEmptyPlaceholders?.();
      window.mzMaterialsReindexSearch?.();

      if(items.some(x => x.kind === 'folder')) location.reload();
    }catch(err){
      alert('No se pudo eliminar: ' + (err.message || err));
    }
  }

  async function createFolder(targetParent = currentFolderPath()){
    targetParent = normPath(targetParent);
    const name = prompt('Nombre de la carpeta:');
    if(!name?.trim()) return;

    try{
      const j = await postForm({
        action:'folder_create',
        folder_parent:targetParent,
        folder_name:name.trim(),
      });
      if(j.node_html){
        ensureSourceChildren(targetParent)?.insertAdjacentHTML('afterbegin', j.node_html);
      }
      refreshExplorer();
    }catch(err){
      alert('No se pudo crear carpeta: ' + (err.message || err));
    }
  }

  function runAction(action, opts = {}){
    const targetPath = opts.useContext ? targetFolderForPaste() : currentFolderPath();
    if(action === 'new-folder') createFolder(targetPath);
    if(action === 'upload') uploadHere(targetPath);
    if(action === 'upload-folder') uploadFolderHere(targetPath);
    if(action === 'google-drive') openGoogleDriveHere(targetPath);
    if(action === 'cut') setClipboard('cut');
    if(action === 'copy') setClipboard('copy');
    if(action === 'paste') pasteClipboard();
    if(action === 'zip-download') downloadZipHere();
    if(action === 'zip-extract') extractSelectedZip();
    if(action === 'access') changeAccess();
    if(action === 'rename') renameSelected();
    if(action === 'delete') deleteSelected();
  }

  function ensureMenu(){
    let menu = $('#mz-explorer-menu');
    if(menu) return menu;

    menu = document.createElement('div');
    menu.id = 'mz-explorer-menu';
    menu.className = 'mz-explorer-menu';
    menu.hidden = true;
    menu.innerHTML = `
      <button type="button" data-explorer-action="new-folder">📁＋ Nueva carpeta</button>
      <button type="button" data-explorer-action="upload">⬆️ Subir aquí</button>
      <button type="button" data-explorer-action="upload-folder">🗂️ Subir carpeta</button>
      <button type="button" data-explorer-action="google-drive">☁️ Google Drive</button>
      <button type="button" data-explorer-action="cut">✂️ Cortar</button>
      <button type="button" data-explorer-action="copy">📄 Copiar</button>
      <button type="button" data-explorer-action="paste">📋 Pegar</button>
      <button type="button" data-explorer-action="zip-download">⬇️ Descargar ZIP</button>
      <button type="button" data-explorer-action="zip-extract">📦 Descomprimir ZIP</button>
      <button type="button" data-explorer-action="access">👥 Acceso...</button>
      <button type="button" data-explorer-action="rename">✏️ Cambiar nombre</button>
      <button type="button" class="danger" data-explorer-action="delete">🗑️ Eliminar</button>
    `;
    document.body.appendChild(menu);
    return menu;
  }

  function closeMenu(){
    const menu = $('#mz-explorer-menu');
    if(menu) menu.hidden = true;
    contextTarget = null;
  }

  function openMenu(x, y){
    const menu = ensureMenu();
    updateToolbar();
    menu.querySelectorAll('[data-explorer-action]').forEach(btn => {
      const action = btn.getAttribute('data-explorer-action');
      const count = selectedItems().length;
      btn.disabled =
        (['cut', 'copy', 'rename', 'delete', 'access'].includes(action) && count === 0) ||
        (['rename', 'access'].includes(action) && count !== 1) ||
        (action === 'zip-extract' && !selectedZipFile()) ||
        (action === 'paste' && !clipboard?.items?.length);
    });

    menu.hidden = false;
    const w = menu.offsetWidth || 190;
    const h = menu.offsetHeight || 220;
    menu.style.left = `${Math.min(x, window.innerWidth - w - 8)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - h - 8)}px`;
  }

  document.addEventListener('click', (e) => {
    const viewBtn = e.target.closest('[data-explorer-view]');
    if(viewBtn){
      e.preventDefault();
      explorerView = viewBtn.getAttribute('data-explorer-view') === 'table' ? 'table' : 'large';
      try { localStorage.setItem(VIEW_KEY, explorerView); } catch(_) {}
      applyExplorerView();
      return;
    }

    const toolbarBtn = e.target.closest('[data-explorer-toolbar] [data-explorer-action]');
    if(toolbarBtn){
      e.preventDefault();
      contextTarget = null;
      runAction(toolbarBtn.getAttribute('data-explorer-action'), { useContext:false });
      return;
    }

    const menuBtn = e.target.closest('#mz-explorer-menu [data-explorer-action]');
    if(menuBtn){
      e.preventDefault();
      const action = menuBtn.getAttribute('data-explorer-action');
      const savedContext = contextTarget;
      closeMenu();
      contextTarget = savedContext;
      runAction(action, { useContext:true });
      contextTarget = null;
      return;
    }

    const explorerBtn = e.target.closest('#mz-explorer-wrap [data-explorer-action]');
    if(explorerBtn){
      e.preventDefault();
      contextTarget = null;
      runAction(explorerBtn.getAttribute('data-explorer-action'), { useContext:false });
      return;
    }

    closeMenu();

    const navBtn = e.target.closest('.mz-explorer-nav-item[data-explorer-open]');
    if(navBtn){
      e.preventDefault();
      setExplorerPath(navBtn.getAttribute('data-explorer-open') || '');
      return;
    }

    const item = itemFromElement(e.target);
    if(!item || isActionTarget(e.target)) return;

    if(e.shiftKey) rangeSelect(item);
    else if(e.ctrlKey || e.metaKey) toggleSelection(item);
    else selectOnly(item);
  }, true);

  document.addEventListener('change', (e) => {
    const sort = e.target.closest('#mz-explorer-sort');
    if(!sort) return;
    explorerSort = sort.value || 'name-asc';
    try { localStorage.setItem(SORT_KEY, explorerSort); } catch(_) {}
    setExplorerPath(explorerPath);
  });

  document.addEventListener('dblclick', (e) => {
    const item = itemFromElement(e.target);
    if(!item || item.kind !== 'folder') return;
    if(!e.target.closest('#mz-explorer-content')) return;
    e.preventDefault();
    setExplorerPath(item.path);
  });

  document.addEventListener('contextmenu', (e) => {
    const item = itemFromElement(e.target);
    const dropTarget = e.target.closest('[data-drop-folder]');
    if(!item && !dropTarget) return;

    e.preventDefault();
    contextTarget = item || dropTarget;

    if(item && !selected.has(keyOf(item))){
      selectOnly(item);
    }else{
      updateToolbar();
    }
    openMenu(e.clientX, e.clientY);
  });

  document.addEventListener('keydown', (e) => {
    if(isTypingTarget(e.target)) return;
    const key = e.key.toLowerCase();

    if(e.key === 'Escape'){
      clearSelection();
      closeMenu();
      return;
    }

    if((e.ctrlKey || e.metaKey) && key === 'c'){
      e.preventDefault();
      setClipboard('copy');
    }
    if((e.ctrlKey || e.metaKey) && key === 'x'){
      e.preventDefault();
      setClipboard('cut');
    }
    if((e.ctrlKey || e.metaKey) && key === 'v'){
      e.preventDefault();
      pasteClipboard();
    }
    if(e.key === 'F2'){
      e.preventDefault();
      renameSelected();
    }
    if(e.key === 'Delete'){
      e.preventDefault();
      deleteSelected();
    }
  });

  document.addEventListener('dragstart', (e) => {
    const item = itemFromElement(e.target);
    if(!item) return;
    if(!e.target.closest('#mz-explorer-content')) return;
    e.stopImmediatePropagation();
    if(!selected.has(keyOf(item))) selectOnly(item);
    const items = selectedItems().map(it => (
      it.kind === 'file' ? { kind:'file', id:it.id } : { kind:'folder', path:it.path }
    ));
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/x-mz-explorer-items', JSON.stringify(items));
  }, true);

  document.addEventListener('dragover', (e) => {
    const target = e.target.closest('#mz-explorer-content, .mz-explorer-nav-item[data-drop-folder], #mz-explorer-content .mz-tree-row[data-drop-folder]');
    if(!target) return;
    const hasExplorerItems = Array.from(e.dataTransfer?.types || []).includes('application/x-mz-explorer-items');
    if(!hasExplorerItems) return;
    e.preventDefault();
    target.classList.add('is-drop-ok');
  }, true);

  document.addEventListener('dragleave', (e) => {
    e.target.closest?.('.is-drop-ok')?.classList.remove('is-drop-ok');
  }, true);

  document.addEventListener('drop', async (e) => {
    const target = e.target.closest('#mz-explorer-content, .mz-explorer-nav-item[data-drop-folder], #mz-explorer-content .mz-tree-row[data-drop-folder]');
    if(!target) return;
    const raw = e.dataTransfer?.getData('application/x-mz-explorer-items') || '';
    if(!raw) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    $$('.is-drop-ok').forEach(el => el.classList.remove('is-drop-ok'));

    let items = [];
    try { items = JSON.parse(raw) || []; } catch(_) {}
    const targetParent = target.hasAttribute('data-drop-folder')
      ? normPath(target.getAttribute('data-drop-folder'))
      : normPath(explorerPath);

    try{
      for(const item of items){
        if(item.kind === 'file') await moveFile(item.id, targetParent);
        if(item.kind === 'folder') await moveFolder(item.path, targetParent);
      }
      try { localStorage.setItem(PATH_KEY, targetParent); } catch(_) {}
      location.reload();
    }catch(err){
      alert('No se pudo mover: ' + (err.message || err));
    }
  }, true);

  document.addEventListener('mz:materials-layout', (e) => {
    if(e.detail?.mode === 'explorer') refreshExplorer();
  });

  try {
    explorerPath = normPath(localStorage.getItem(PATH_KEY) || '');
    explorerView = localStorage.getItem(VIEW_KEY) === 'table' ? 'table' : 'large';
    explorerSort = localStorage.getItem(SORT_KEY) || 'name-asc';
  } catch(_) {}
  if(!['name-asc', 'time-desc', 'time-asc', 'size-desc', 'size-asc'].includes(explorerSort)){
    explorerSort = 'name-asc';
  }
  refreshExplorer();
  updateToolbar();
})();
