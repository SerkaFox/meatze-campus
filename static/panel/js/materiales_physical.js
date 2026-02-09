/* static/panel/js/materiales_physical.js */
(() => {
  'use strict';
  if (window.__MZ_MATERIALES_PHYSICAL__) return;
  window.__MZ_MATERIALES_PHYSICAL__ = true;

  // Делегированный клик по кнопкам "Descargar DOCX" (material físico)
  // В шаблоне кнопка:
  // <button type="button"
  //   data-action="mz.download.acta"
  //   data-codigo="{{ curso.codigo }}"
  //   data-item-key="{{ it.key }}">
  //   Descargar DOCX
  // </button>

  function mzDownloadPhysicalActa(codigo, itemKey){
    // (опционально) если когда-то добавишь input даты:
    // <input class="mz-phys-date" data-item-key="..." value="YYYY-MM-DD">
    const inp = document.querySelector(
      `.mz-phys-date[data-item-key="${CSS.escape(itemKey)}"]`
    );
    const fecha = inp && inp.value ? inp.value : '';

    const qs = new URLSearchParams();
    qs.set('item_key', itemKey);
    if (fecha) qs.set('fecha', fecha);

    // teacher-only view, использует cookie-сессию
    const url =
      `/alumno/curso/${encodeURIComponent(codigo)}/physical_report_doc/?` +
      qs.toString();

    window.location.href = url; // скачивание
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="mz.download.acta"]');
    if (!btn) return;
    e.preventDefault();

    const codigo = (btn.getAttribute('data-codigo') || '').trim();
    const itemKey = (btn.getAttribute('data-item-key') || '').trim();

    if (!codigo || !itemKey) {
      alert('Falta codigo o item_key');
      return;
    }

    mzDownloadPhysicalActa(codigo, itemKey);
  });
})();