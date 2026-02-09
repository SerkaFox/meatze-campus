/* static/panel/js/materiales.js */
(() => {
  'use strict';
  if (window.__MZ_MATERIALES_PAGE__) return;
  window.__MZ_MATERIALES_PAGE__ = true;

  const $  = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

  // ---------------------------------------
  // 1) Modules dropdown (MF/UF menu sizing + open/close)
  // ---------------------------------------
  (function initModulesDropdown(){
    const dd = document.getElementById('mz-mod-dd');
    const btn = document.getElementById('mz-mod-btn');
    const menu = document.getElementById('mz-mod-menu');
    if (!dd || !btn || !menu) return;

    function calcMenuWidth(){
      const wasOpen = menu.classList.contains('is-open');
      if (!wasOpen) {
        menu.style.visibility = 'hidden';
        menu.classList.add('is-open');
      }

      let maxW = 0;
      menu.querySelectorAll('a').forEach(a => {
        maxW = Math.max(maxW, a.scrollWidth);
      });

      const padding = 32;
      const target = Math.ceil(maxW + padding);

      const btnW = btn.getBoundingClientRect().width;
      const finalW = Math.max(target, Math.ceil(btnW), 260);

      menu.style.width = finalW + 'px';

      if (!wasOpen) {
        menu.classList.remove('is-open');
        menu.style.visibility = '';
      }
    }

    function open(){ calcMenuWidth(); menu.classList.add('is-open'); }
    function close(){ menu.classList.remove('is-open'); }
    function toggle(){ menu.classList.contains('is-open') ? close() : open(); }

    btn.addEventListener('click', (e)=>{ e.preventDefault(); toggle(); });
    btn.addEventListener('keydown', (e)=>{
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      if (e.key === 'Escape') close();
    });

    document.addEventListener('click', (e)=>{
      if (!dd.contains(e.target)) close();
    });

    menu.addEventListener('click', (e)=>{
      const a = e.target.closest('a[data-mod]');
      if (a) close();
    });
  })();

  // -----------------------------
  // Layout toggle: tree <-> cards
  // -----------------------------
  (function initLayoutToggle(){
    const treeWrap  = document.getElementById('mz-tree-wrap');
    const cardsWrap = document.getElementById('mz-cards-wrap');
    if(!treeWrap || !cardsWrap) return;

    const KEY = 'mz_materiales_layout_v1';

    function setLayout(mode){
      const isCards = (mode === 'cards');
      treeWrap.hidden  = isCards;
      cardsWrap.hidden = !isCards;

      document.querySelectorAll('[data-layout]').forEach(b=>{
        b.classList.toggle('is-act', b.getAttribute('data-layout') === mode);
      });

      try{ localStorage.setItem(KEY, mode); }catch(_){}
    }

    document.addEventListener('click', (e)=>{
      const btn = e.target.closest('[data-layout]');
      if(!btn) return;
      e.preventDefault();
      setLayout(btn.getAttribute('data-layout'));
    });

    let saved = 'tree';
    try{ saved = localStorage.getItem(KEY) || 'tree'; }catch(_){}
    if(saved !== 'tree' && saved !== 'cards') saved = 'tree';
    setLayout(saved);
  })();
// ---------------------------------------
// 6) URL upload AJAX: upload by link + insert into DOM (no reload)
// ---------------------------------------
(function initUrlUploadAjax(){
  const form = document.getElementById('mz-upload-form');
  if(!form) return;

  const urlInp = form.querySelector('input[data-role="url"]');
  const titleInp = form.querySelector('input[data-role="url_title"]');
  const submitBtn = document.getElementById('mzf-send');

  const csrftoken = (document.cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith('csrftoken='))||'')
    .split('=')[1] || '';

  function toast(msg, ok=true){
    let el = document.getElementById('mz-toast');
    if(!el){
      el = document.createElement('div');
      el.id = 'mz-toast';
      el.style.cssText = `
        position:fixed; right:16px; bottom:16px; z-index:9999;
        padding:10px 12px; border-radius:12px;
        background:rgba(15,23,42,.92); color:#e5e7eb;
        border:1px solid rgba(148,163,184,.25);
        box-shadow:0 12px 30px rgba(0,0,0,.35);
        font-size:.9rem; max-width:360px;
      `;
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.borderColor = ok ? 'rgba(34,197,94,.45)' : 'rgba(239,68,68,.45)';
    el.style.display = 'block';
    clearTimeout(el.__t);
    el.__t = setTimeout(()=>{ el.style.display='none'; }, 1600);
  }

  function ensureTreeContainer(folderPath){
    const p = (folderPath || '').trim();
    if(!p){
      let root = document.querySelector('.mz-tree-rootfiles');
      if(!root){
        root = document.createElement('div');
        root.className = 'mz-tree-rootfiles';
        const tree = document.querySelector('.mz-tree');
        if(tree) tree.prepend(root);
      }
      return root;
    }

    const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(p)}"]`);
    if(!node) return null;

    let kids = node.querySelector(':scope > .mz-tree-children');
    if(!kids){
      kids = document.createElement('div');
      kids.className = 'mz-tree-children';
      node.appendChild(kids);
    }

    kids.hidden = false;
    const tgl = node.querySelector('[data-toggle]');
    if(tgl) tgl.textContent = '▾';
    return kids;
  }

  form.addEventListener('submit', async (e)=>{
    const url = (urlInp?.value || '').trim();
    if(!url) return; // пусть твоя валидация/UX решает

    e.preventDefault();

    const old = submitBtn ? submitBtn.textContent : '';
    if(submitBtn){ submitBtn.disabled = true; submitBtn.textContent = 'Subiendo...'; }

    try{
      const fd = new FormData(form);

      const r = await fetch(window.location.pathname + window.location.search, {
        method:'POST',
        credentials:'include',
        headers:{
          'X-CSRFToken': decodeURIComponent(csrftoken || ''),
          'X-Requested-With':'XMLHttpRequest',
        },
        body: fd
      });

      const txt = await r.text();
      let j = {};
      try{ j = txt ? JSON.parse(txt) : {}; }catch(_){}
      if(!r.ok || !j.ok) throw new Error(j.error || j.message || ('HTTP ' + r.status));

      if(j.file_html){
        const container = ensureTreeContainer(j.folder_path || '');
        if(container){
          container.insertAdjacentHTML('afterbegin', j.file_html);
          window.mzMaterialsFsBindDropTargets?.();
          window.mzMaterialsReindexSearch?.();
          window.mzCleanupEmptyPlaceholders?.();
          if(j.folder_path) window.mzBumpCountCascade?.(j.folder_path, +1);
        }
      }

      if(urlInp) urlInp.value = '';
      if(titleInp) titleInp.value = '';

      toast('Archivo añadido ✓', true);
    }catch(err){
      console.error(err);
      toast('No se pudo subir: ' + (err.message || err), false);
    }finally{
      if(submitBtn){ submitBtn.disabled = false; submitBtn.textContent = old; }
    }
  });
})();
})();