/* static/panel/js/materiales_gdrive.js */
(() => {
  'use strict';
  if (window.__MZ_GDRIVE_IMPORT__) return;
  window.__MZ_GDRIVE_IMPORT__ = true;

  const GDRIVE_FOLDER_MIME = 'application/vnd.google-apps.folder';

  const cfg = document.getElementById('mz-gdrive-cfg');
  if (!cfg) return;

  const CLIENT_ID = (cfg.getAttribute('data-client-id') || '').trim();
  const API_KEY   = (cfg.getAttribute('data-api-key') || '').trim();
  const APP_ID    = (cfg.getAttribute('data-app-id') || '').trim();

  if (!CLIENT_ID || !API_KEY || !APP_ID) return;
  let currentDriveImportJob = null;
  let gisInited = false;
  let pickerInited = false;
  let tokenClient = null;
  let accessToken = '';
  let gisRequestInFlight = false;
const TOKEN_KEY = 'mz_gdrive_access_token';
const TOKEN_EXP_KEY = 'mz_gdrive_access_token_exp';

function saveToken(token, expiresInSec){
  accessToken = token || '';
  window.__MZ_GDRIVE_TOKEN__ = accessToken;

  if (accessToken){
    sessionStorage.setItem(TOKEN_KEY, accessToken);

    const expTs = Date.now() + Math.max(0, (Number(expiresInSec || 0) - 60)) * 1000;
    sessionStorage.setItem(TOKEN_EXP_KEY, String(expTs));
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_EXP_KEY);
  }
}

function restoreToken(){
  const token = sessionStorage.getItem(TOKEN_KEY) || '';
  const expTs = Number(sessionStorage.getItem(TOKEN_EXP_KEY) || 0);

  if (!token || !expTs) return false;
  if (Date.now() >= expTs){
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_EXP_KEY);
    return false;
  }

  accessToken = token;
  window.__MZ_GDRIVE_TOKEN__ = token;
  return true;
}

function clearToken(){
  saveToken('', 0);
}
  let pendingTargetPath = '';
  let pendingPickKind = 'file';
restoreToken();

window.mzGoogleDriveListFolderUrl = function(){
  const codigo = window.mzGetCursoCodigo();
  if(!codigo) throw new Error('No se pudo detectar código del curso');
  return `/alumno/curso/${encodeURIComponent(codigo)}/materiales/drive/list-folder/`;
};

window.mzGoogleDriveCreateFolderUrl = function(){
  const codigo = window.mzGetCursoCodigo();
  if(!codigo) throw new Error('No se pudo detectar código del curso');
  return `/alumno/curso/${encodeURIComponent(codigo)}/materiales/drive/create-folder/`;
};

async function createMeatzeFolder(parentPath, name){
  return window.mzPostJSON(window.mzGoogleDriveCreateFolderUrl(), {
    parent_path: parentPath || '',
    name: name || 'Carpeta'
  }, window.mzCsrfToken());
}
async function listDriveFolderChildren(folderId){
  return window.mzPostJSON(window.mzGoogleDriveListFolderUrl(), {
    folder_id: folderId,
    access_token: accessToken
  }, window.mzCsrfToken());
}

  window.mzGoogleDriveImportFolderUrl = function(){
    const codigo = window.mzGetCursoCodigo();
    if(!codigo) throw new Error('No se pudo detectar código del curso');
    return `/alumno/curso/${encodeURIComponent(codigo)}/materiales/drive/import-folder/`;
  };

  function $(s, r=document){ return r.querySelector(s); }
  function $$(s, r=document){ return Array.from(r.querySelectorAll(s)); }

  function normPath(p){
    return String(p || '').trim().replace(/^\/+|\/+$/g, '');
  }

  function getCurrentPath(){
    const btnTarget = normPath(window.__MZ_GDRIVE_BUTTON_TARGET__ || '');
    if (btnTarget || window.__MZ_GDRIVE_BUTTON_TARGET__ === '') {
      return btnTarget;
    }

    const bc = document.getElementById('mz-fold-bc');
    const fromBc = bc ? (bc.getAttribute('data-path') || '') : '';
    return normPath(window.__MZ_CARDS_MOUNT_PATH__ || fromBc || '');
  }

  function getAllFolderPaths(){
    const nodes = Array.from(document.querySelectorAll('.mz-tree-node[data-node]'));
    const paths = nodes
      .map(n => normPath(n.getAttribute('data-node') || ''))
      .filter(Boolean);

    const uniq = Array.from(new Set(paths));
    uniq.sort((a,b) => a.localeCompare(b, undefined, { numeric:true, sensitivity:'base' }));
    return uniq;
  }

  function humanPath(path){
    const p = normPath(path);
    return p || 'Raíz';
  }

  function createDriveProgressJob(jobId, kind){
    const fileSteps = [
      { percent: 6,  meta: 'Conectando con Google Drive…' },
      { percent: 16, meta: 'Preparando importación…' },
      { percent: 32, meta: 'Descargando archivo desde Google Drive…' },
      { percent: 52, meta: 'Guardando en MEATZE…' },
      { percent: 72, meta: 'Procesando archivo…' },
      { percent: 88, meta: 'Finalizando importación…' },
    ];

    const folderSteps = [
      { percent: 5,  meta: 'Conectando con Google Drive…' },
      { percent: 12, meta: 'Leyendo carpeta…' },
      { percent: 24, meta: 'Creando estructura en MEATZE…' },
      { percent: 40, meta: 'Importando archivos…' },
      { percent: 58, meta: 'Procesando contenido…' },
      { percent: 76, meta: 'Guardando en MEATZE…' },
      { percent: 90, meta: 'Finalizando carpeta…' },
    ];

    const steps = kind === 'folder' ? folderSteps : fileSteps;
    let idx = 0;
    let stopped = false;

    window.mzUploadOverlay.setUploading(jobId, {
      percent: 2,
      meta: kind === 'folder'
        ? 'Iniciando importación de carpeta…'
        : 'Iniciando importación de archivo…'
    });

    const timer = setInterval(() => {
      if (stopped) return;
      if (idx >= steps.length) return;
      const step = steps[idx++];
      window.mzUploadOverlay.setUploading(jobId, {
        percent: step.percent,
        meta: step.meta
      });
    }, 900);

    return {
      finish(meta){
        if (stopped) return;
        stopped = true;
        clearInterval(timer);
        window.mzUploadOverlay.setDone(jobId, {
          meta: meta || 'Importación completada'
        });
      },
      fail(message){
        if (stopped) return;
        stopped = true;
        clearInterval(timer);
        window.mzUploadOverlay.setError(jobId, message || 'Error importando desde Google Drive');
      }
    };
  }

  function loadScript(src){
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing){
        if (existing.dataset.loaded === '1') return resolve();
        existing.addEventListener('load', resolve, { once:true });
        existing.addEventListener('error', reject, { once:true });
        return;
      }

      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.defer = true;
      s.onload = () => {
        s.dataset.loaded = '1';
        resolve();
      };
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function ensureGoogleApis(){
    if (!window.google?.accounts?.oauth2){
      await loadScript('https://accounts.google.com/gsi/client');
    }

    if (!window.gapi){
      await loadScript('https://apis.google.com/js/api.js');
    }

    if (!window.google?.accounts?.oauth2){
      throw new Error('Google Identity Services no se cargó');
    }

    if (!window.gapi){
      throw new Error('Google API client no se cargó');
    }

    if (!pickerInited){
      await new Promise((resolve, reject) => {
        try{
          window.gapi.load('picker', { callback: resolve });
        }catch(err){
          reject(err);
        }
      });
      pickerInited = true;
    }

    if (!gisInited){
      tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: 'https://www.googleapis.com/auth/drive.readonly',
        callback: (resp) => {
          gisRequestInFlight = false;

          if (!resp || resp.error || !resp.access_token){
            console.error('[GIS callback error]', resp);
            alert('Google no devolvió un token válido.');
            return;
          }

          saveToken(resp.access_token, resp.expires_in || 3600);

          openPicker(pendingTargetPath, pendingPickKind);
        },
		error_callback: (err) => {
		  gisRequestInFlight = false;
		  clearToken();
		  console.error('[GIS error_callback]', err);

		  if (err?.type === 'popup_closed') return;
		  alert('No se pudo iniciar Google Drive.');
		}
      });

      gisInited = true;
    }
  }

  function insertImportedFiles(j, targetPath){
    const container =
      window.mzFindTargetContainer?.(targetPath) ||
      window.__MZ_CARDS_MOUNT_EL__ ||
      document.querySelector('.mz-tree-rootfiles');

    if (!container || !Array.isArray(j?.files)) return;

    let added = 0;
    for (const it of j.files){
      if (it?.file_html){
        container.insertAdjacentHTML('afterbegin', it.file_html);
        added += 1;
      }
    }

    if (targetPath){
      if (typeof window.mzBumpCount === 'function') {
        window.mzBumpCount(targetPath, +added, 'direct');
      }
      if (typeof window.mzBumpCountCascadeTotal === 'function') {
        window.mzBumpCountCascadeTotal(targetPath, +added);
      }
    }

    window.mzMaterialsSyncCardsFromTree?.();
    window.mzMaterialsFsBindDropTargets?.();
    window.mzMaterialsReindexSearch?.();
  }

function importPickedFileSilent(doc, targetPath){
  const fileId = doc.id;
  const name = doc.name || 'drive_file';
  const mimeType = doc.mimeType || '';
  const sizeBytes = Number(doc.sizeBytes || doc.size || 0);

  const importUrl = window.mzGoogleDriveImportUrl();

  return window.mzPostJSON(importUrl, {
    file_id: fileId,
    name,
    mime_type: mimeType,
    size_bytes: sizeBytes,
    folder_path: targetPath || '',
    audience: (window.__MZ_AUD__ || 'alumnos'),
    access_token: accessToken
  }, window.mzCsrfToken())
  .then((j) => {
    insertImportedFiles(j, targetPath);
    return j;
  });
}

function importPickedFile(doc, targetPath){
  const name = doc.name || 'drive_file';
  const sizeBytes = Number(doc.sizeBytes || doc.size || 0);

  const jobId = window.mzUploadOverlay.addJob({
    name,
    meta: `Preparando Google Drive · destino: ${humanPath(targetPath)}`
  });

  const progress = createDriveProgressJob(jobId, 'file');

  return importPickedFileSilent(doc, targetPath)
    .then((j) => {
      progress.finish(
        sizeBytes > 0
          ? `Importado en ${humanPath(targetPath)} · ${window.mzBytesHuman ? window.mzBytesHuman(sizeBytes) : ''}`.trim()
          : `Importado en ${humanPath(targetPath)}`
      );
      return j;
    })
    .catch((err) => {
      progress.fail(err.message || 'Error importando archivo');
      throw err;
    });
}

  function importPickedFolder(doc, targetPath){
    const folderId = doc.id;
    const name = doc.name || doc[window.google.picker.Document.NAME] || 'Carpeta';

    const importUrl = window.mzGoogleDriveImportFolderUrl();

    const jobId = window.mzUploadOverlay.addJob({
      name,
      meta: `Preparando carpeta de Google Drive · destino: ${humanPath(targetPath)}`
    });

    const progress = createDriveProgressJob(jobId, 'folder');

    return window.mzPostJSON(importUrl, {
      folder_id: folderId,
      name,
      folder_path: targetPath || '',
      audience: (window.__MZ_AUD__ || 'alumnos'),
      access_token: accessToken
    }, window.mzCsrfToken())
    .then((j) => {
      window.mzMaterialsSyncCardsFromTree?.();
      window.mzMaterialsFsBindDropTargets?.();
      window.mzMaterialsReindexSearch?.();

      progress.finish(
        `Carpeta importada en ${humanPath(targetPath)} · ${j.files_created || 0} archivos · ${j.folders_created || 0} carpetas`
      );

      location.reload();
    })
    .catch((err) => {
      progress.fail(err.message || 'Error importando carpeta');
      throw err;
    });
  }

  function openPicker(targetPath, kind){
    if (!window.google?.picker){
      alert('Google Picker todavía no está disponible.');
      return;
    }

    const docsView = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
      .setIncludeFolders(true)
      .setSelectFolderEnabled(kind === 'folder');

    if (kind === 'folder'){
      docsView.setMimeTypes(GDRIVE_FOLDER_MIME);
    } else {
      // обычные файлы + google docs и т.д., но не папки
      // picker всё равно может показывать папки для навигации, но выбор папки не активен
    }

    const picker = new window.google.picker.PickerBuilder()
      .setAppId(APP_ID)
      .setDeveloperKey(API_KEY)
      .setOAuthToken(accessToken)
      .addView(docsView)
      .enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED)
      .setCallback(async (data) => {
        if (data.action !== window.google.picker.Action.PICKED) return;

        const docs = data.docs || [];
        for (const doc of docs){
          try{
            const mimeType = doc.mimeType || doc[window.google.picker.Document.MIME_TYPE] || '';
			if (kind === 'folder' || mimeType === GDRIVE_FOLDER_MIME){
			  await importPickedFolderIncremental(doc, targetPath);
			} else {
			  await importPickedFile(doc, targetPath);
			}
          }catch(err){
            console.error(err);
            alert('No se pudo importar desde Google Drive: ' + (err.message || err));
          }
        }
      })
      .build();

    picker.setVisible(true);
  }

function ensureTokenAndOpen(targetPath, pickKind){
  if (!tokenClient){
    alert('Google Drive todavía no está listo.');
    return;
  }

  pendingTargetPath = targetPath || '';
  pendingPickKind = pickKind || 'file';
  window.__MZ_GDRIVE_TARGET_PATH__ = pendingTargetPath;

  // есть живой токен
  if (accessToken || restoreToken()){
    openPicker(pendingTargetPath, pendingPickKind);
    return;
  }

  if (gisRequestInFlight) return;
  gisRequestInFlight = true;

  // сначала тихо
  tokenClient.callback = (resp) => {
    gisRequestInFlight = false;

    if (!resp || resp.error || !resp.access_token){
      console.warn('[GIS silent failed]', resp);

      // fallback с consent
      gisRequestInFlight = true;
      tokenClient.callback = (resp2) => {
        gisRequestInFlight = false;

        if (!resp2 || resp2.error || !resp2.access_token){
          clearToken();
          console.error('[GIS consent callback error]', resp2);
          alert('Google no devolvió un token válido.');
          return;
        }

        saveToken(resp2.access_token, resp2.expires_in || 3600);
        openPicker(pendingTargetPath, pendingPickKind);
      };

      tokenClient.requestAccessToken({ prompt: 'consent' });
      return;
    }

    saveToken(resp.access_token, resp.expires_in || 3600);
    openPicker(pendingTargetPath, pendingPickKind);
  };

  tokenClient.requestAccessToken({ prompt: '' });
}

  function initLauncherModal(){
    const modal = document.getElementById('mz-gdrive-launcher');
    if (!modal) return;

    // ✅ ВАЖНО: выносим модалку в body, чтобы её не ломали parent overflow/transform
    if (modal.parentElement !== document.body){
      document.body.appendChild(modal);
    }

    const closeEls = $$('[data-close]', modal);
    const kindWrap = $('#mz-gdrive-kind', modal);
    const confirmBtn = $('#mz-gdrive-launch-confirm', modal);
    const currentPathLabel = $('#mz-gdrive-current-path-label', modal);
    const destPreview = $('#mz-gdrive-dest-preview', modal);
    const folderSelect = $('#mz-gdrive-folder-select', modal);

    function fillFolders(){
      if (!folderSelect) return;

      const currentValue = folderSelect.value;
      const paths = getAllFolderPaths();

      folderSelect.innerHTML = `<option value="">Raíz</option>`;
      paths.forEach(path => {
        const opt = document.createElement('option');
        opt.value = path;
        opt.textContent = path;
        folderSelect.appendChild(opt);
      });

      if (paths.includes(currentValue)) folderSelect.value = currentValue;
    }

    function getSelectedKind(){
      const act = kindWrap?.querySelector('[data-kind].is-act');
      return act ? (act.getAttribute('data-kind') || 'file') : 'file';
    }

    function getSelectedTargetPath(){
      const mode = modal.querySelector('input[name="mz_gdrive_dest_mode"]:checked')?.value || 'current';
      const current = getCurrentPath();

      if (mode === 'root') return '';
      if (mode === 'current') return current;
      if (mode === 'custom') return normPath(folderSelect?.value || '');
      return current;
    }

    function refreshUi(){
      const current = getCurrentPath();
      if (currentPathLabel) currentPathLabel.textContent = humanPath(current);
      if (destPreview) destPreview.textContent = humanPath(getSelectedTargetPath());
    }

    function open(){
      fillFolders();
      refreshUi();
      modal.classList.remove('is-hidden');
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('mz-modal-open');

      const card = modal.querySelector('.mz-prev-card');
      if (card) card.scrollTop = 0;

      confirmBtn?.focus();
    }

    function close(){
      modal.classList.add('is-hidden');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('mz-modal-open');
      window.__MZ_GDRIVE_BUTTON_TARGET__ = undefined;
    }

    closeEls.forEach(el => {
      el.addEventListener('click', close);
    });

    modal.addEventListener('click', (e) => {
      if (e.target.matches('.mz-prev-backdrop')) close();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('is-hidden')) close();
    });

    kindWrap?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-kind]');
      if (!btn) return;

      $$('[data-kind]', kindWrap).forEach(x => x.classList.remove('is-act'));
      btn.classList.add('is-act');
    });

    modal.addEventListener('change', (e) => {
      if (
        e.target.matches('input[name="mz_gdrive_dest_mode"]') ||
        e.target.matches('#mz-gdrive-folder-select')
      ){
        refreshUi();
      }
    });

    confirmBtn?.addEventListener('click', async () => {
      const targetPath = getSelectedTargetPath();
      const pickKind = getSelectedKind();

      close();
      window.__MZ_GDRIVE_BUTTON_TARGET__ = undefined;
      try{
        await ensureGoogleApis();
        ensureTokenAndOpen(targetPath, pickKind);
      }catch(err){
        console.error(err);
        alert('No se pudo abrir Google Drive: ' + (err.message || err));
      }
    });

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="folder.upload.google"]');
      if (!btn) return;

      e.preventDefault();

      const explicitParent = normPath(btn.getAttribute('data-parent') || '');
      window.__MZ_GDRIVE_BUTTON_TARGET__ = explicitParent;

      open();
    });
  }

  initLauncherModal();

  ensureGoogleApis().catch(err => {
    console.error('[GDrive preload failed]', err);
  });


async function importPickedFolderIncremental(doc, targetPath){

  const rootFolderId = doc.id;
  const rootFolderName = doc.name || 'Carpeta';

  currentDriveImportJob = {
    cancelled: false
  };

  const progressJobId = window.mzUploadOverlay.addJob({
    name: rootFolderName,
    meta: `Preparando carpeta de Google Drive · destino: ${humanPath(targetPath)}`
  });

  // 👇 обработчик отмены
  window.mzUploadOverlay.onCancel(progressJobId, () => {

    if(!currentDriveImportJob) return;

    const ok = confirm('¿Cancelar la importación de Google Drive?');
    if(!ok) return;

    currentDriveImportJob.cancelled = true;

  });

  let foldersDone = 0;
  let filesDone = 0;

  function updateProgress(meta, percent){
    window.mzUploadOverlay.setUploading(progressJobId,{
      percent: Math.max(2, Math.min(98, percent || 2)),
      meta
    });
  }

  async function walkFolder(driveFolderId, driveFolderName, meatzeParentPath){
if(currentDriveImportJob?.cancelled){
  throw new Error("Importación cancelada por el usuario");
}
    const safeName = String(driveFolderName || 'Carpeta').trim() || 'Carpeta';

    const created = await createMeatzeFolder(meatzeParentPath, safeName);

    const currentMeatzePath =
      created.path ||
      (meatzeParentPath ? `${meatzeParentPath}/${safeName}` : safeName);

    foldersDone++;

    updateProgress(
      `Carpetas: ${foldersDone} · Archivos: ${filesDone}`,
      Math.min(15 + foldersDone * 2 + filesDone, 90)
    );

    const listed = await listDriveFolderChildren(driveFolderId);
    const items = Array.isArray(listed.items) ? listed.items : [];

    for(const item of items){

        if(currentDriveImportJob?.cancelled){
			throw new Error("Importación cancelada");
		  }

  if(item.mimeType === GDRIVE_FOLDER_MIME){

        await walkFolder(
          item.id,
          item.name || 'Carpeta',
          currentMeatzePath
        );

      }else{

        await importPickedFileSilent({
          id: item.id,
          name: item.name || 'file',
          mimeType: item.mimeType || '',
          size: Number(item.size || 0)
        }, currentMeatzePath);
if(currentDriveImportJob?.cancelled){
  throw new Error("Importación cancelada");
}
        filesDone++;

        updateProgress(
          `Carpetas: ${foldersDone} · Archivos: ${filesDone}`,
          Math.min(20 + foldersDone * 2 + filesDone, 96)
        );

      }
    }
  }


  try{

    await walkFolder(rootFolderId, rootFolderName, targetPath || '');

    window.mzUploadOverlay.setDone(progressJobId,{
      meta: `Carpeta importada · ${filesDone} archivos · ${foldersDone} carpetas`
    });

    location.reload();

  }catch(err){

  if(currentDriveImportJob?.cancelled){
    window.mzUploadOverlay.setError(
      progressJobId,
      "Importación cancelada"
    );
    return;
  }

  window.mzUploadOverlay.setError(
    progressJobId,
    err.message || 'Error importando carpeta'
  );

  throw err;
}
}
})();