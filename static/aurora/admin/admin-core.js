(()=>{ 'use strict';
  // === helpers ===
  const $  = (s,root=document)=>root.querySelector(s);
  const $$ = (s,root=document)=>Array.from(root.querySelectorAll(s));

  // В Django нет /wp-json, поэтому сразу:
  const API_BASE = '/v5';
  const API_A    = API_BASE + '/admin';

const KEY = 'mz_admin';
const KEY_REM = 'mz_admin_remember';

const rememberEl = () => document.getElementById('adm-remember');
const wantRemember = () => !!rememberEl()?.checked;

const tok = () =>
  sessionStorage.getItem(KEY) ||
  localStorage.getItem(KEY) ||
  '';

const setTok = (t) => {
  // всегда кладём в session (совместимость со старыми модулями)
  sessionStorage.setItem(KEY, t);

  // если "запомнить" — кладём ещё и в local
  localStorage.setItem(KEY_REM, wantRemember() ? '1' : '0');
  if (wantRemember()) localStorage.setItem(KEY, t);
  else localStorage.removeItem(KEY);
};

const clearTok = () => {
  sessionStorage.removeItem(KEY);
  localStorage.removeItem(KEY);
  localStorage.removeItem(KEY_REM);
};

const qs = (bust=false) => (bust ? `?_=${Date.now()}` : '');

  const auth   = (isPost=false)=>{
    const h={};
    if (tok()) h['X-MZ-Admin'] = tok();
    if (isPost) h['Content-Type'] = 'application/json';
    return h;
  };

  async function ping(){
    const r = await fetch(`${API_A}/ping${qs(true)}`, {
      headers: auth(), cache:'no-store'
    });
    if (!r.ok) throw new Error('bad');
  }

  // === UI refs ===
  const gate  = $('#adm-shared-gate');
  const pills = document.getElementById('adm-pills');
  const pillBtns = pills ? $$('.pill', pills) : []; // <= важно: защищаемся, если ещё нет DOM

  // === Password field show/hide ===
  $('#adm-eye-shared')?.addEventListener('click', ()=>{
    const inp  = $('#adm-pass-shared');
    const show = inp.type === 'password';
    inp.type   = show ? 'text' : 'password';
    $('#adm-eye-shared').textContent = show ? '🙈' : '👁';
  });

  // === Apply shared auth ===
  async function tryTokenShared(pwd){
    if (!pwd) return false;
    setTok(pwd);          // храним ПЛЕЙН, сервер сверяет с AURORA_ADMIN_PASS
    try{
      await ping();
document.getElementById('adm-shell')?.classList.remove('is-locked');


      // спрячем любые другие «гейты» на странице, если вдруг есть
      ['#adm-gate','#mzs-gate'].forEach(sel=>{
        const el = document.querySelector(sel);
        if (el && el !== gate) el.style.display = 'none';
      });

      // показываем пилюли, инициализируем панели
      if (gate) gate.style.display = 'none';
      if (pills) pills.style.display = 'block';

      initPanelsOnce();

      const last = localStorage.getItem('mz_admin_last') || 'cursos';
      showPanel(last);
window.AURORA = window.AURORA || {};
window.AURORA.HELP_UI = "admin_mod:" + (last || "cursos");
      document.dispatchEvent(new CustomEvent('mz:admin-auth', {detail:{ok:true}}));
      return true;
    }catch(_){
      clearTok();
      return false;
    }
  }

  $('#adm-enter-shared')?.addEventListener('click', async ()=>{
    const msg = $('#adm-gate-msg');
    if (msg) msg.textContent = '';
    const pwd = ($('#adm-pass-shared')?.value || '').trim();
    if (!pwd){
      if (msg) msg.textContent = 'Introduce la contraseña';
      return;
    }
    const ok = await tryTokenShared(pwd);
    if (!ok && msg) msg.textContent = 'Contraseña incorrecta';
  });

  $('#adm-pass-shared')?.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter'){
      e.preventDefault();
      $('#adm-enter-shared')?.click();
    }
  });

	// восстановим чекбокс "Recordarme"
	const remEl = rememberEl();
	if (remEl) remEl.checked = (localStorage.getItem(KEY_REM) === '1');

	// авто-вход, если токен уже есть (в нужном storage)
	if (tok()){
	  tryTokenShared(tok());
	}

  // === PANELS MAP ===
const map = {
  teachers:'ui-teachers',
  cursos:'ui-cursos',
  horarios:'ui-horarios',
  subs:'ui-subs',
  wa:'ui-wa',
  lanbide:'ui-lanbide',
};
const actionsTitle = document.getElementById('mz-admin-actions-title');
const actionGroups = $$('.mz-actions-group');
const actionTitles = {
  teachers: 'Docentes',
  cursos: 'Cursos',
  horarios: 'Horarios',
  lanbide: 'Lanbide',
  subs: 'Subs',
  wa: 'WhatsApp',
};

  function normalizeMod(mod){
    const wanted = String(mod || 'cursos');
    const btn = pillBtns.find(b => b.dataset.mod === wanted);
    if (!map[wanted] || !btn || btn.hidden) return 'cursos';
    return wanted;
  }

  function showPanel(mod){
  if (!pills) return;
  mod = normalizeMod(mod);

  // 1️⃣ выключаем ВСЕ панели
  Object.values(map).forEach(id=>{
    const el = document.getElementById(id);
    if (!el) return;
    el.dataset.active = 'false';   // ← КЛЮЧЕВО
  });

  // 2️⃣ включаем нужную
  const pane = document.getElementById(map[mod]);
  if (pane){
    pane.dataset.active = 'true';  // ← КЛЮЧЕВО
    pane.dispatchEvent(new CustomEvent('mz:pane:show', {
      bubbles:true,
      detail:{mod}
    }));
  }

  if (actionsTitle) actionsTitle.textContent = actionTitles[mod] || 'Panel';
  actionGroups.forEach(group=>{
    group.hidden = group.dataset.actionsFor !== mod;
  });

  // 3️⃣ активная pill
  pillBtns.forEach(b=>{
    b.setAttribute(
      'aria-current',
      b.dataset.mod === mod ? 'true' : 'false'
    );
  });
// --- pills micro-anim + underline slider ---
try{
  const bar = document.querySelector('#adm-pills .pillbar');
  const active = pillBtns.find(b => b.dataset.mod === mod);
  if (bar && active){
    // pop animation
    active.classList.remove('is-pop');
    void active.offsetWidth;
    active.classList.add('is-pop');
    setTimeout(()=>active.classList.remove('is-pop'), 260);

    // underline position (учитывает 2 ряда)
    const x = active.offsetLeft;
    const y = active.offsetTop + active.offsetHeight + 6; // ✅ под активной кнопкой, даже на 2-й строке
    bar.style.setProperty('--mz-pill-x', `${Math.round(x)}px`);
    bar.style.setProperty('--mz-pill-y', `${Math.round(y)}px`);
    bar.style.setProperty('--mz-pill-w', `${Math.round(active.offsetWidth)}px`);
  }
}catch(_){}

  localStorage.setItem('mz_admin_last', mod);
}
window.MZAdminShowPanel = showPanel;
window.addEventListener('resize', ()=>{
  const last = localStorage.getItem('mz_admin_last') || 'cursos';
  // просто переустановит underline по текущей активной pill
  
  showPanel(last);
  window.AURORA = window.AURORA || {};
window.AURORA.HELP_UI = "admin_mod:" + (last || "cursos");
}, {passive:true});


  function initPanelsOnce(){
    if (!pills) return;                 // если HTML ещё не нарисовался
    if (pills.dataset.init === '1') return;
    pills.dataset.init = '1';


    // спрячем все панели по умолчанию
    Object.values(map).forEach(id=>{
      const el = document.getElementById(id);
      if (el){
        el.classList.add('mz-pane');
        el.dataset.active = 'false';
      }
    });
  }
// Делегирование кликов по pills
document.addEventListener('click', (e)=>{
  const btn = e.target.closest('#adm-pills .pill');
  if (!btn) return;
  const mod = btn.dataset.mod;
  if (mod) showPanel(mod);
});

document.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-admin-action-click]');
  if (!btn) return;
  const target = document.querySelector(btn.dataset.adminActionClick);
  if (target) target.click();
});

document.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-admin-anchor]');
  if (!btn) return;
  const before = btn.dataset.adminClickBefore;
  if (before) document.querySelector(before)?.click();
  setTimeout(()=>{
    const target = document.querySelector(btn.dataset.adminAnchor);
    target?.scrollIntoView({behavior:'smooth', block:'start'});
    if (target){
      target.classList.remove('mz-anchor-pulse');
      void target.offsetWidth;
      target.classList.add('mz-anchor-pulse');
      window.setTimeout(()=> target.classList.remove('mz-anchor-pulse'), 1700);
    }
  }, before ? 80 : 0);
});

document.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-guide-step]');
  if (!btn) return;
  const step = btn.dataset.guideStep;
  if (step === 'teachers') showPanel('teachers');
  if (step === 'horarios') showPanel('horarios');
  if (step === 'cursos-form' || step === 'cursos-assign') {
    showPanel('cursos');
    setTimeout(()=>{
      const target = step === 'cursos-assign' ? '#mzc-tab-assign' : '#mzc-tab-form';
      document.querySelector(target)?.click();
      document.getElementById('ui-cursos')?.scrollIntoView({behavior:'smooth', block:'start'});
    }, 40);
  }
});

  // если DOM уже загружен – сразу инициализируем панели; если нет – дождёмся
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initPanelsOnce);
  } else {
    initPanelsOnce();
  }
    const rem = localStorage.getItem(KEY_REM) === '1';
  if (rememberEl()) rememberEl().checked = rem;

  if (!sessionStorage.getItem(KEY) && rem && localStorage.getItem(KEY)) {
    sessionStorage.setItem(KEY, localStorage.getItem(KEY));
  }
})();


(function(){
  window.AURORA = window.AURORA || {};

  const KEY = "mz_help_ui_last";

  function setUI(v){
    window.AURORA.HELP_UI = v || "";
    try { localStorage.setItem(KEY, window.AURORA.HELP_UI); } catch(_){}
  }

  function getUrlTab(){
    try {
      const u = new URL(location.href);
      return u.searchParams.get("tab") || "";
    } catch(_) { return ""; }
  }

  function detectActiveTabFromDom(){
    // подстрой под твои вкладки:
    // 1) aria-current
    const a = document.querySelector('[data-tab][aria-current="true"]');
    if (a) return a.getAttribute("data-tab") || "";
    // 2) class active
    const b = document.querySelector('[data-tab].active, [data-tab].is-active');
    if (b) return b.getAttribute("data-tab") || "";
    return "";
  }

  // ✅ 1) init on load
  const urlTab = getUrlTab();
  const domTab = detectActiveTabFromDom();
  const saved = (function(){ try { return localStorage.getItem(KEY) || ""; } catch(_) { return ""; } })();

  const initial = urlTab
    ? `tab:${urlTab}`
    : domTab
      ? `tab:${domTab}`
      : saved
        ? saved
        : "tab:info"; // <-- дефолт

  setUI(initial);

  // ✅ 2) update on tab clicks (делегирование)
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-tab]");
    if (t){
      const tab = t.getAttribute("data-tab") || "";
      if (tab) setUI(`tab:${tab}`);
      return;
    }
  });

})();
