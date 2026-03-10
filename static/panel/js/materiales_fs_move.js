(() => {
'use strict';

if (window.__MZ_FS_MOVE__) return;
window.__MZ_FS_MOVE__ = true;

document.addEventListener('dragstart', (e) => {
  const handle = e.target.closest('[data-drag-folder]');
  if (!handle) return;

  const path = handle.dataset.dragFolder;
  if (!path) return;

  e.dataTransfer.setData('text/mz-folder', path);
  e.dataTransfer.effectAllowed = 'move';
});

document.addEventListener('dragover', (e) => {
  const target = e.target.closest('[data-drop-folder]');
  if (!target) return;

  // реагируем только на drag папки
  const hasFolderDrag = Array.from(e.dataTransfer?.types || []).includes('text/mz-folder');
  if (!hasFolderDrag) return;

  e.preventDefault();

  document
    .querySelectorAll('.is-drop-target')
    .forEach(el => el.classList.remove('is-drop-target'));

  target.classList.add('is-drop-target');
});

document.addEventListener('drop', async (e) => {
  const target = e.target.closest('[data-drop-folder]');
  if (!target) return;

  const source = e.dataTransfer?.getData('text/mz-folder') || '';
  if (!source) return;

  e.preventDefault();
  e.stopPropagation();

  document
    .querySelectorAll('.is-drop-target')
    .forEach(el => el.classList.remove('is-drop-target'));

  const targetParent = target.dataset.dropFolder || '';
  if (source === targetParent) return;

  const codigo = window.__MZ_CURSO_CODIGO__;
  const url = `/alumno/curso/${encodeURIComponent(codigo)}/materiales/fs/move-folder/`;

  try {
    const r = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.mzCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({
        source_path: source,
        target_parent: targetParent
      })
    });

    const txt = await r.text();
    let j = {};
    try { j = txt ? JSON.parse(txt) : {}; } catch(_) {}

	if (!r.ok || !j.ok) {
		alert(j.message || 'No se pudo mover la carpeta');
	  return;
	}

    const node = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(j.old_path)}"]`);
if (!node) {
  location.reload();
  return;
}

function ensureFolderChildrenContainer(parentPath){
  if (!parentPath) {
    let root = document.querySelector('.mz-tree-rootfolders');
    if (!root) {
      root = document.createElement('div');
      root.className = 'mz-tree-rootfolders';
      document.querySelector('.mz-tree')?.prepend(root);
    }
    return root;
  }

  const parentNode = document.querySelector(`.mz-tree-node[data-node="${CSS.escape(parentPath)}"]`);
  if (!parentNode) return null;

  let kids = parentNode.querySelector(':scope > .mz-tree-children');
  if (!kids) {
    kids = document.createElement('div');
    kids.className = 'mz-tree-children';
    parentNode.appendChild(kids);
  }

  kids.hidden = false;
  const tgl = parentNode.querySelector(':scope [data-toggle]');
  if (tgl) tgl.textContent = '▾';

  return kids;
}

function renameDomPaths(rootNode, oldBase, newBase){
  const nodes = [rootNode, ...rootNode.querySelectorAll('.mz-tree-node[data-node]')];

  nodes.forEach(el => {
    const oldPath = (el.getAttribute('data-node') || '').trim();
    if (!oldPath) return;

    let newPath = oldPath;
    if (oldPath === oldBase) {
      newPath = newBase;
    } else if (oldPath.startsWith(oldBase + '/')) {
      newPath = newBase + oldPath.slice(oldBase.length);
    }

    el.setAttribute('data-node', newPath);

    const row = el.querySelector(':scope > .mz-tree-row');
    if (row && row.hasAttribute('data-drop-folder')) {
      row.setAttribute('data-drop-folder', newPath);
    }

    const dragHandle = el.querySelector(':scope [data-drag-folder]');
    if (dragHandle) {
      dragHandle.setAttribute('data-drag-folder', newPath);
    }
  });
}

const targetContainer = ensureFolderChildrenContainer(targetParent);
if (!targetContainer) {
  location.reload();
  return;
}

renameDomPaths(node, j.old_path, j.new_path);
targetContainer.prepend(node);

window.mzMaterialsReindexSearch?.();
window.mzMaterialsSyncCardsFromTree?.();
window.mzCleanupEmptyPlaceholders?.();
window.mzMaterialsFsBindDropTargets?.();
  } catch (err) {
    console.error(err);
    alert('Error al mover la carpeta');
  }
});

document.addEventListener('dragend', () => {
  document
    .querySelectorAll('.is-drop-target')
    .forEach(el => el.classList.remove('is-drop-target'));
});

})();