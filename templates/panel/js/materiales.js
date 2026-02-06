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

  // ---------------------------------------
  // 2) Apply selected module_key to upload rows + URL section
  // ---------------------------------------
  (function initApplySelectedModule(){
    const filters = document.querySelector('.mz-mat-modfilters[data-selected-mod]');
    if (!filters) return;

    function getSelected(){
      return (filters.getAttribute('data-selected-mod') || '').trim();
    }

    function applyToRow(row, selected){
      const mk = row.querySelector('[data-role="module_key"]');
      if (!mk) return;
      mk.value = selected || '';
    }

    function applyAll(){
      const selected = getSelected();
      if (!selected || selected === 'none') return;

      const rowsContainer = document.getElementById('mz-upl-rows');
      if (rowsContainer) $$('.mz-upl-row', rowsContainer).forEach(r=>applyToRow(r, selected));

      const urlMk = document.querySelector('#mz-upload-form [data-role="url_module_key"]');
      if (urlMk) urlMk.value = selected;
    }

    // first pass
    applyAll();

    // keep in sync if rows are added dynamically
    const rowsContainer = document.getElementById('mz-upl-rows');
    if (rowsContainer) {
      const mo = new MutationObserver((muts)=>{
        for (const m of muts) {
          if (m.type === 'childList' && m.addedNodes && m.addedNodes.length) {
            applyAll();
            break;
          }
        }
      });
      mo.observe(rowsContainer, { childList:true });
    }
  })();


  // ---------------------------------------
  // 3) Upload rows: drop input holds multi, then distribute files into single-file rows
  // ---------------------------------------
  (function initUploadRowsDistributor(){
    const rowsContainer = document.getElementById('mz-upl-rows');
    if (!rowsContainer) return;

    function setSingleFile(input, file){
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    }

    function clearFileInput(input){
      try { input.value = ''; } catch(e) {}
      const dt = new DataTransfer();
      input.files = dt.files;
    }

    function removeRowHandler(row){
      const removeBtn = row.querySelector('.mz-upl-remove-row');
      if (removeBtn) {
        removeBtn.addEventListener('click', (e)=>{
          e.preventDefault();
          row.remove();
        });
      }
    }

    function addRowFromTemplate(){
      const template = rowsContainer.children[0];
      if (!template) return null;

      const idx = rowsContainer.children.length + 1;
      const clone = template.cloneNode(true);

      // remove dropzone from clones
      const dz = clone.querySelector('[data-role="dropzone"]');
      if (dz) dz.remove();

      // show file input (template hides it)
      const fileInput = clone.querySelector('[data-role="file"]');
      if (fileInput) fileInput.style.display = '';

      clone.setAttribute('data-row-idx', String(idx));

      clone.querySelectorAll('[data-role]').forEach((el)=>{
        const role = el.getAttribute('data-role');
        if (!role) return;
        el.name = role + '_' + idx;

        if (role === 'file') {
          el.value = '';
          el.removeAttribute('multiple'); // single file per row
        }
        if (role === 'title') el.value = '';
        if (role === 'module_key') el.value = '';
      });

      rowsContainer.appendChild(clone);
      removeRowHandler(clone);
      return clone;
    }

    // bind remove for existing row too
    $$('.mz-upl-row', rowsContainer).forEach(removeRowHandler);

    const firstRow = rowsContainer.querySelector('.mz-upl-row');
    if (!firstRow) return;

    const firstFileInput = firstRow.querySelector('[data-role="file"]');
    if (!firstFileInput) return;

    const dropLabel = firstRow.querySelector('[data-role="droplabel"]');
    const dropSub   = firstRow.querySelector('[data-role="dropsub"]');
    const countEl   = firstRow.querySelector('[data-role="dropcount"]');
    const clearBtn  = firstRow.querySelector('[data-role="dropclear"]');

    function resetDropUI(){
      if (dropLabel) dropLabel.textContent = 'Arrastra y suelta archivos';
      if (dropSub) dropSub.textContent = 'o haz clic para seleccionarlos (multi)';
      if (countEl) countEl.textContent = '0';
    }

    function moveFilesToRows(files){
      if (!files || !files.length) return;

      for (let i = 0; i < files.length; i++) {
        const row = addRowFromTemplate();
        if (!row) break;
        const inp = row.querySelector('[data-role="file"]');
        if (inp) setSingleFile(inp, files[i]);
      }

      clearFileInput(firstFileInput);
      resetDropUI();
    }

    firstFileInput.addEventListener('change', ()=>{
      const files = Array.from(firstFileInput.files || []);
      if (!files.length) { resetDropUI(); return; }

      if (countEl) countEl.textContent = String(files.length);
      if (dropLabel) dropLabel.textContent = files.length === 1 ? files[0].name : `${files.length} archivos`;
      if (dropSub) dropSub.textContent = files.length > 1 ? 'Se repartirán en filas abajo' : 'Se añadirá una fila abajo';

      moveFilesToRows(files);
    });

    if (clearBtn){
      clearBtn.addEventListener('click', (e)=>{
        e.preventDefault();
        e.stopPropagation();
        clearFileInput(firstFileInput);
        resetDropUI();
      });
    }

    resetDropUI();
  })();


  // ---------------------------------------
  // 4) Dropzone UX: click opens file chooser + drag/drop sets FileList and triggers change
  // ---------------------------------------
  (function initDropzone(){
    const rowsContainer = document.getElementById('mz-upl-rows');
    if (!rowsContainer) return;

    const firstRow = rowsContainer.querySelector('.mz-upl-row');
    if (!firstRow) return;

    const drop = firstRow.querySelector('[data-role="dropzone"]');
    const countEl = firstRow.querySelector('[data-role="dropcount"]');
    const input = firstRow.querySelector('[data-role="file"]');
    if (!drop || !input) return;

    drop.addEventListener('click', ()=> input.click());

    function setCount(n){
      if (countEl) countEl.textContent = String(n || 0);
    }

    input.addEventListener('change', ()=> setCount((input.files && input.files.length) || 0));

    const stop = (e) => { e.preventDefault(); e.stopPropagation(); };

    ['dragenter','dragover'].forEach(evt=>{
      drop.addEventListener(evt, (e)=>{
        stop(e);
        drop.classList.add('is-over');
      });
    });

    ['dragleave','dragend','drop'].forEach(evt=>{
      drop.addEventListener(evt, (e)=>{
        stop(e);
        drop.classList.remove('is-over');
      });
    });

    drop.addEventListener('drop', (e)=>{
      stop(e);
      const files = e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files : null;
      if (!files || !files.length) return;

      const dt = new DataTransfer();
      for (const f of files) dt.items.add(f);
      input.files = dt.files;

      setCount(dt.files.length);

      // distributor will split rows
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  })();


  // ---------------------------------------
  // 5) Upload form validation: require at least one file or URL
  // ---------------------------------------
  (function initUploadValidation(){
    const form = document.getElementById('mz-upload-form');
    if (!form) return;

    const urlInp = form.querySelector('input[data-role="url"]');
    const rows = document.getElementById('mz-upl-rows');
    const firstRow = rows ? rows.querySelector('.mz-upl-row') : null;
    const drop = firstRow ? firstRow.querySelector('[data-role="dropzone"]') : null;

    function anyFileSelected(){
      const inputs = form.querySelectorAll('input[type="file"][data-role="file"]');
      for (const inp of inputs){
        if (inp.files && inp.files.length) return true;
      }
      return false;
    }

    function hasUrl(){
      return !!(urlInp && urlInp.value && urlInp.value.trim().length);
    }

    form.addEventListener('submit', (e)=>{
      if (anyFileSelected() || hasUrl()) return;

      e.preventDefault();
      if (drop){
        drop.classList.add('is-over');
        setTimeout(()=>drop.classList.remove('is-over'), 350);
      }
      alert('Sube un archivo o pega una URL.');
    });
  })();

})();