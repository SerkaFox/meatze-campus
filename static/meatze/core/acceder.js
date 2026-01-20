/* static/meatze/pages/acceder.js */
(() => {
  'use strict';
  if (window.__MZ_ACCEDER_V2__) return;
  window.__MZ_ACCEDER_V2__ = true;

  const $ = (s) => document.querySelector(s);

  const WP_ROOT = (window.wpApiSettings && wpApiSettings.root)
    ? wpApiSettings.root
    : (location.origin + '/');
  const V5 = WP_ROOT.replace(/\/$/, '') + '/meatze/v5';

  // ===== same fetch helper style as original modal =====
  async function api(url, opt = {}) {
    const o = Object.assign({ credentials: 'include', cache: 'no-store' }, opt);

    if ((!o.method || o.method === 'GET') && typeof URL === 'function') {
      const u = new URL(url, window.location.origin);
      u.searchParams.set('_', Date.now().toString());
      url = u.toString();
    }

    o.headers = Object.assign({ 'Cache-Control': 'no-cache' }, o.headers || {});
    const isV5 = /\/meatze\/v5\//.test(url);
    const isPublic = /\/meatze\/v5\/(?:cursos|curso|me|auth\/)/.test(url);

    if (isV5 && window.mzRestNonce && !isPublic) o.headers['X-WP-Nonce'] = window.mzRestNonce;
    if (!isV5 && window.wpApiSettings?.nonce)   o.headers['X-WP-Nonce'] = window.wpApiSettings.nonce;

    if (o.body && typeof o.body !== 'string' && !(o.body instanceof FormData)) {
      o.headers['Content-Type'] = 'application/json';
      o.body = JSON.stringify(o.body);
    }

    const r = await fetch(url, o);
    const t = await r.text();
    let j = null;
    try { j = JSON.parse(t); } catch (_) {}
    if (!r.ok) throw (j || { status: r.status, text: t });
    return j || {};
  }

  // in original code mzApi was alias
  async function mzApi(_actionKey, url, opt = {}) {
    return api(url, opt);
  }

  // ===== UI helpers =====
  const STEPS = ['#step-email', '#step-temp', '#step-temp-finish', '#step-setpass'];
  function showStep(sel) {
    for (const s of STEPS) {
      const el = $(s);
      if (!el) continue;
      el.style.display = (s === sel) ? '' : 'none';
    }
  }

  function qNext() {
    const u = new URL(location.href);
    return u.searchParams.get('next') || '';
  }
function finishAuthRedirect() {
  const u = new URL(location.href);
  if (u.searchParams.get('tab') === 'profile') return; // на профиле НЕ редиректим

  const next = u.searchParams.get('next') || '';
  location.replace(next || '/alumno/');
}


  function validEmail(e) {
    e = (e || '').trim().toLowerCase();
    return !!e && e.includes('@') && e.length >= 5;
  }

  function revealInit() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.mz-reveal[data-target]');
      if (!btn) return;
      const inp = document.querySelector(btn.getAttribute('data-target'));
      if (!inp) return;
      inp.type = (inp.type === 'text') ? 'password' : 'text';
      btn.setAttribute('aria-pressed', String(inp.type === 'text'));
      try { inp.focus({ preventScroll: true }); } catch (_) {}
    });
  }

  // ===== AUTH (password / pin) =====
  let LAST_EMAIL = null;
  let LAST_PIN = null;
  let MUST_SET = false;

  async function apiLoginPassword() {
    const emailEl = $('#auth-email');
    const passEl  = $('#auth-pass-login');
    const msgPwd  = $('#msg-pass-login');

    const email = (emailEl.value || '').trim().toLowerCase();
    const pwd   = (passEl.value  || '').trim();

    msgPwd.textContent = '';
    if (!validEmail(email)) { msgPwd.textContent = 'E-mail inválido'; return; }
    if (!pwd) { msgPwd.textContent = 'Introduce la contraseña'; return; }

    try {
      const j = await mzApi('auth.login_password', V5 + '/auth/login_password', {
        method: 'POST',
        body: { email, password: pwd }
      });

      if (j?.me) {
        try { localStorage.setItem('mz_me', JSON.stringify(j.me)); } catch (_) {}
      }
      window.dispatchEvent(new CustomEvent('meatze:authChanged', { detail: Object.assign({ logged_in: true }, j?.me || {}) }));
      finishAuthRedirect();
    } catch (e) {
      msgPwd.textContent = e?.message || 'Credenciales inválidas.';
    }
  }

  async function requestPIN() {
    const emailEl = $('#auth-email');
    const msgPwd  = $('#msg-pass-login');
    const pinWrap = $('#pin-wrap');
    const pinEl   = $('#auth-pin');
    const msgPin  = $('#msg-pin');

    msgPwd.textContent = '';
    msgPin.textContent = '';

    const email = (emailEl.value || '').trim().toLowerCase();
    if (!validEmail(email)) { msgPwd.textContent = 'E-mail inválido'; return; }

    try {
      await mzApi('auth.request_pin', V5 + '/auth/request_pin', { method: 'POST', body: { email } });
      pinWrap.style.display = 'block';
      msgPin.textContent = 'PIN enviado (válido 10 min).';
      pinEl.focus();
    } catch (e) {
      msgPwd.textContent = e?.message || 'No se pudo enviar el PIN.';
    }
  }

  async function verifyPIN() {
    const emailEl = $('#auth-email');
    const pinEl   = $('#auth-pin');
    const msgPin  = $('#msg-pin');
    const setWrap = $('#step-setpass');

    msgPin.textContent = '';

    const email = (emailEl.value || '').trim().toLowerCase();
    const pin   = (pinEl.value || '').replace(/\D/g, '').slice(0, 6);

    if (!validEmail(email)) { msgPin.textContent = 'E-mail inválido'; return; }
    if (pin.length !== 6) { msgPin.textContent = 'PIN debe tener 6 dígitos'; return; }

    try {
      const j = await api(V5 + '/auth/verify_pin', { method: 'POST', body: { email, pin } });

      LAST_EMAIL = email;
      LAST_PIN   = pin;

      // me from response or fallback /me
      let me = j?.me || null;
      if (!me) {
        try {
          const me2 = await api(V5 + '/me');
          me = me2?.me || me2 || null;
        } catch (_) {}
      }

      const isTeacher   = !!(me && (me.is_teacher === true || me.is_teacher == 1));
      const hasPassword = !!(me && (me.has_password === true || me.has_password == 1));
      MUST_SET = !!(isTeacher && !hasPassword);

      const note = setWrap?.querySelector('.mz-ok');
      if (note) {
        note.textContent = MUST_SET
          ? 'Sesión iniciada. Como docente, define una contraseña (obligatorio).'
          : 'Sesión iniciada. Puedes definir una contraseña para próximos accesos (opcional).';
      }

      showStep('#step-setpass');
    } catch (e) {
      msgPin.textContent = e?.message || 'PIN incorrecto o caducado.';
    }
  }

  async function setPassword() {
    const setPass = $('#auth-pass');
    const msgSet  = $('#msg-setpass');

    const p = (setPass.value || '').trim();
    msgSet.textContent = '';

    if (p.length < 6) { msgSet.textContent = 'Mínimo 6 caracteres'; return; }

    try {
      const body = { password: p };
      if (LAST_EMAIL && LAST_PIN) { body.email = LAST_EMAIL; body.pin = LAST_PIN; }

      await mzApi('auth.set_password', V5 + '/auth/set_password', { method: 'POST', body });

      msgSet.textContent = 'Contraseña guardada. Entrando…';
      finishAuthRedirect();
    } catch (e) {
      msgSet.textContent = e?.message || 'Error';
    }
  }

  // ===== TEMP (crear cuenta alumno) — FIXED endpoints =====
  async function loadTempNamesForCourse() {
    const selCourse = $('#temp-course');
    const selName   = $('#temp-name');
    const msgTemp   = $('#msg-temp');

    msgTemp.textContent = 'Cargando…';
    selName.innerHTML = '';

    const code = selCourse.value;
    if (!code) { msgTemp.textContent = ''; return; }

    try {
      const r = await api(V5 + '/auth/temp_accounts?course_code=' + encodeURIComponent(code));
      const names = Array.isArray(r.items) ? r.items : [];
      if (!names.length) {
        msgTemp.textContent = 'No hay cuentas temporales disponibles.';
        return;
      }
      selName.innerHTML = names.map(n => `<option value="${n}">${n}</option>`).join('');
      msgTemp.textContent = '';
    } catch (e) {
      msgTemp.textContent = 'No se pudo cargar alumnos.';
    }
  }

let __TEMP_COURSES = []; // [{code,title,label}]

function renderCourseOptions(list){
  const selCourse = $('#temp-course');
  if (!selCourse) return;

  if (!Array.isArray(list) || !list.length) {
    selCourse.innerHTML = `<option value="" disabled selected>Sin resultados</option>`;
    return;
  }

  selCourse.innerHTML = list.map(it => {
    const code  = (it.code || '').trim();
    const title = (it.title || '').trim();
    const label = it.label || (title ? `${title} — ${code}` : code);
    return `<option value="${code}">${label}</option>`;
  }).join('');
}


function filterCourses(query){
  query = (query || '').trim().toLowerCase();
  if (!query) return __TEMP_COURSES;

  const starts = [];
  const includes = [];

  for (const it of __TEMP_COURSES) {
    const code = String(it.code || '').toLowerCase();
    const title = String(it.title || '').toLowerCase();
    const label = String(it.label || '').toLowerCase();
    const hay = `${code} ${title} ${label}`;

    if (code.startsWith(query)) starts.push(it);
    else if (hay.includes(query)) includes.push(it);
  }
  return starts.concat(includes);
}


function bindCourseSearch(){
  const inp = $('#temp-course-search');
  const sel = $('#temp-course');
  if (!inp || !sel) return;

  let t = null;
  inp.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(async () => {
      const filtered = filterCourses(inp.value);
      renderCourseOptions(filtered);

      // если после фильтра что-то есть — обновим зависимые поля
      renderSelectedCourseCode();
      await loadTempNamesForCourse();
    }, 60);
  });

  // удобство: Enter → фокус на select
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); sel.focus(); }
  });
}


function renderSelectedCourseCode(){
  const sel = $('#temp-course');
  const box = $('#temp-course-code');
  if (!sel || !box) return;
  const code = sel.value || '';
  box.textContent = code ? `Código: ${code}` : '';
}


async function openTemp() {
  const selCourse = $('#temp-course');
  const msgTemp   = $('#msg-temp');
  const searchInp = $('#temp-course-search');

  if (!selCourse) {
    console.error('temp: #temp-course not found in DOM');
    msgTemp && (msgTemp.textContent = 'Falta el selector de curso en la página.');
    return;
  }

  msgTemp.textContent = '';
  try {
    const r = await api(V5 + '/auth/temp_cursos');
    const items = Array.isArray(r.items) ? r.items : [];

	__TEMP_COURSES = items.map(it => {
	  // API может вернуть строку или объект с разными полями
	  if (typeof it === 'string') {
		const code = it.trim();
		return { code, title: '', label: code };
	  }

	  const code  = String(it.codigo || it.code || it.course_code || it.slug || '').trim();
	  const title = String(it.titulo || it.title || it.nombre || it.name || '').trim();

	  const label = title ? `${title} — ${code}` : (code || title || '');
	  return { code, title, label };
	}).filter(x => x.code || x.title);


    renderCourseOptions(__TEMP_COURSES);

    // биндим поиск один раз
    if (!window.__TEMP_SEARCH_BOUND__) {
      window.__TEMP_SEARCH_BOUND__ = true;
      bindCourseSearch();
    }

    // очистить поиск при открытии, чтобы показывать все курсы
    if (searchInp) searchInp.value = '';

    await loadTempNamesForCourse();
    renderSelectedCourseCode();

    showStep('#step-temp');
    try { (searchInp || selCourse).focus(); } catch (_) {}
  } catch (e) {
    console.error('temp_cursos error', e);
    msgTemp.textContent = 'No se pudo cargar cursos.';
  }
}


  async function tempVerify() {
    const stepTemp = $('#step-temp');
    const selCourse = $('#temp-course');
    const selName = $('#temp-name');
    const inpCode = $('#temp-code');
    const msgTemp = $('#msg-temp');
    const inpFull = $('#temp-fullname');
    const inpPass = $('#temp-pass');

    const code = selCourse.value;
    const tname = selName.value;
    const key = (inpCode.value || '').replace(/\D/g, '').slice(0, 2);

    msgTemp.textContent = '';
    if (!code || !tname || key.length !== 2) {
      msgTemp.textContent = 'Completa los campos.';
      return;
    }

    try {
      await mzApi('auth.temp_verify', V5 + '/auth/temp_verify', {
        method: 'POST',
        body: { course_code: code, temp_name: tname, key }
      });

      stepTemp.dataset.course = code;
      stepTemp.dataset.tname  = tname;
      stepTemp.dataset.key    = key;

      inpFull.value = '';
      inpPass.value = '';

      showStep('#step-temp-finish');
    } catch (e) {
      msgTemp.textContent =
        e?.code === 'gone'      ? 'Este código ya fue usado o caducó.' :
        e?.code === 'forbidden' ? 'Código incorrecto. Revisa los 2 dígitos.' :
        e?.code === 'not_found' ? 'Curso o cuenta temporal no encontrada.' :
        (e?.message || 'No se pudo verificar el código.');

      if (e?.code === 'forbidden') {
        inpCode.classList.add('error');
        setTimeout(() => inpCode.classList.remove('error'), 1500);
      }
    }
  }

  async function tempClaim() {
    const stepTemp = $('#step-temp');
    const stepFin  = $('#step-temp-finish');

    const inpFull = $('#temp-fullname');
    const inpPass = $('#temp-pass');
    const msgTempFin = $('#msg-temp-finish');

    const code = stepTemp.dataset.course;
    const tname = stepTemp.dataset.tname;
    const key = stepTemp.dataset.key;

    const full = (inpFull.value || '').trim();
    const pass = (inpPass.value || '').trim();

    msgTempFin.textContent = '';
    if (!full || pass.length < 6) {
      msgTempFin.textContent = 'Indica nombre y contraseña (min. 6).';
      return;
    }

    try {
      const j = await mzApi('auth.temp_claim', V5 + '/auth/temp_claim', {
        method: 'POST',
        body: { course_code: code, temp_name: tname, key, full_name: full, password: pass }
      });

      const createdEmail = j?.email || '(desconocido)';

      // (опционально) красивый экран “Cuenta creada” — как в оригинале
      stepFin.innerHTML = `
        <div class="mz-ok" style="margin-bottom:10px">Cuenta creada.</div>
        <div class="mz-help" style="margin-bottom:8px">Guarda estos datos para entrar más tarde:</div>

        <label class="mz-help">Usuario (e-mail de acceso)</label>
        <div style="display:flex; gap:8px; align-items:center;">
          <input id="new-email-display" class="mz-inp" value="${createdEmail}" readonly onclick="this.select()">
          <button class="mz-btn mz-copy" type="button" data-copy-target="#new-email-display">Copiar</button>
        </div>

        <label class="mz-help" style="margin-top:8px">Contraseña</label>
        <div style="display:flex; gap:8px; align-items:center; width:100%;">
          <div class="mz-field" style="flex:1;">
            <input id="new-pass-display" class="mz-inp" type="password" value="${pass}" readonly>
            <button class="mz-reveal" type="button" aria-label="Mostrar contraseña" data-target="#new-pass-display">
              <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            </button>
          </div>
          <button class="mz-btn mz-copy" type="button" data-copy-target="#new-pass-display">Copiar</button>
        </div>

        <div class="mz-help" style="margin-top:12px"><strong>Nota:</strong> este e-mail <u>NO</u> es un correo real; es tu <em>usuario de acceso</em>.</div>

        <label class="mz-help" style="display:flex;gap:8px;align-items:center;margin-top:12px">
          <input type="checkbox" id="ack-saved">
          He guardado mi usuario y contraseña
        </label>

        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
          <button id="btn-go-panel" class="mz-btn" type="button" disabled>Entrar al panel</button>
          <button id="btn-go-login" class="mz-btn ghost sm" type="button">Volver</button>
        </div>

        <div id="msg-temp-finish" class="mz-help"></div>
      `;

      const ack = $('#ack-saved');
      const goPanel = $('#btn-go-panel');
      ack?.addEventListener('change', () => { goPanel.disabled = !ack.checked; });
      goPanel?.addEventListener('click', () => finishAuthRedirect());
      $('#btn-go-login')?.addEventListener('click', () => location.reload());

      // copy buttons
      document.addEventListener('click', (e) => {
        const b = e.target.closest('.mz-copy[data-copy-target]');
        if (!b) return;
        const inp = document.querySelector(b.getAttribute('data-copy-target'));
        if (!inp) return;
        try { inp.select(); document.execCommand('copy'); } catch (_) {}
      });

    } catch (e) {
      msgTempFin.textContent = e?.message || 'No se pudo crear la cuenta.';
    }
  }

  function bind() {
  revealInit();
const card = document.querySelector('.mz-auth-card');
if (card) {
  card.addEventListener('mousemove', (e) => {
    const r = card.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    card.style.transform = `translateY(-2px) rotateX(${(-y*6).toFixed(2)}deg) rotateY(${(x*8).toFixed(2)}deg)`;
  });
  card.addEventListener('mouseleave', () => {
    card.style.transform = '';
  });
}

	  // Если открыли /acceder/?tab=profile — показываем профиль и НЕ трогаем шаги логина
	  const u = new URL(location.href);
	  if (u.searchParams.get('tab') === 'profile') {
		initProfileTabRouting();
		return;
	  }

	  // дальше как было...
	  if ($('#step-email')) showStep('#step-email');

    // auth
    $('#btn-login-pass')?.addEventListener('click', apiLoginPassword);
    $('#btn-send-pin')  ?.addEventListener('click', requestPIN);
    $('#btn-resend')    ?.addEventListener('click', requestPIN);
    $('#btn-verify')    ?.addEventListener('click', verifyPIN);
    $('#btn-setpass')   ?.addEventListener('click', setPassword);


// === ENTER to submit (login / pin / temp) ===
function bindEnterSubmit() {
  const onEnter = (el, fn) => {
    if (!el) return;
    el.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      fn();
    });
  };

  // login by password: Enter on email or password
  onEnter($('#auth-email'), apiLoginPassword);
  onEnter($('#auth-pass-login'), apiLoginPassword);

  // pin: Enter on pin => verify
  onEnter($('#auth-pin'), verifyPIN);

  // set password: Enter => setPassword
  onEnter($('#auth-pass'), setPassword);

  // temp flow: Enter on code => tempVerify, Enter on pass => tempClaim
  onEnter($('#temp-code'), tempVerify);
  onEnter($('#temp-pass'), tempClaim);
}

bindEnterSubmit();


    $('#btn-done')?.addEventListener('click', () => {
      const msgSet = $('#msg-setpass');
      if (MUST_SET) {
        msgSet.textContent = 'Como docente, primero define una contraseña.';
        try { $('#auth-pass')?.focus(); } catch (_) {}
        return;
      }
      finishAuthRedirect();
    });

    // temp
    $('#btn-open-temp') ?.addEventListener('click', openTemp);
    $('#temp-course')?.addEventListener('change', async () => {
	  renderSelectedCourseCode();
	  await loadTempNamesForCourse();
	});

    $('#btn-temp-back') ?.addEventListener('click', () => showStep('#step-email'));
    $('#btn-temp-check')?.addEventListener('click', tempVerify);
    $('#btn-temp-finish')?.addEventListener('click', tempClaim);
    $('#btn-temp-cancel')?.addEventListener('click', () => showStep('#step-email'));
	initProfileTabRouting();

  }
// ===== PROFILE TAB =====
function setTab(tab){
  const login = document.getElementById('mz-tab-login');
  const prof  = document.getElementById('mz-tab-profile');
  const title = document.getElementById('mz-auth-title');

  if (!login || !prof) return;

  if (tab === 'profile') {
    login.style.display = 'none';
    prof.style.display = '';
    if (title) title.textContent = 'Datos personales';
  } else {
    prof.style.display = 'none';
    login.style.display = '';
    if (title) title.textContent = 'Acceso';
  }
}

async function loadProfile(){
  const msgTop = document.getElementById('mz-prof-msg');

  const fFirst = document.getElementById('prof-first');
  const fLast1 = document.getElementById('prof-last1');
  const fLast2 = document.getElementById('prof-last2');
  const fDisp  = document.getElementById('prof-display');
  const fBio   = document.getElementById('prof-bio');

  if (!fFirst || !fLast1) return;

  msgTop && (msgTop.textContent = 'Cargando…');

  try{
    const p = await api(V5 + '/me/profile');     // ✅ КАК В ОРИГИНАЛЕ
    const pr = p.profile || p;

    fFirst.value = pr.first_name   || '';
    fLast1.value = pr.last_name1   || '';
    if (fLast2) fLast2.value = pr.last_name2 || '';
    if (fDisp)  fDisp.value  = pr.display_name || '';
    if (fBio)   fBio.value   = pr.bio || '';

    msgTop && (msgTop.textContent = '');
  } catch(e){
    msgTop && (msgTop.textContent = e?.message || 'No se pudo cargar el perfil.');
  }
}


async function saveProfile(){
  const msgTop = document.getElementById('mz-prof-msg');
  const msgPass= document.getElementById('mz-prof-pass-msg');

  const fFirst = document.getElementById('prof-first');
  const fLast1 = document.getElementById('prof-last1');
  const fLast2 = document.getElementById('prof-last2');
  const fDisp  = document.getElementById('prof-display');
  const fBio   = document.getElementById('prof-bio');
  const p1     = (document.getElementById('prof-pass1')?.value || '').trim();
  const p2     = (document.getElementById('prof-pass2')?.value || '').trim();

  const btn = document.getElementById('btn-prof-save');
  if (!fFirst || !fLast1) return;

  if (msgTop) msgTop.textContent = '';
  if (msgPass) msgPass.textContent = '';

  // валидация пароля как в оригинале :contentReference[oaicite:3]{index=3}
  if (p1 || p2){
    if (p1.length < 6){
      if (msgPass) msgPass.textContent = 'Contraseña mínima 6 caracteres.';
      return;
    }
    if (p1 !== p2){
      if (msgPass) msgPass.textContent = 'Las contraseñas no coinciden.';
      return;
    }
  }

  const body = {
    first_name:   fFirst.value || '',
    last_name1:   fLast1.value || '',
    last_name2:   fLast2?.value || '',
    display_name: fDisp?.value  || '',
    bio:          fBio?.value   || '',
  };

  if (btn){
    btn.disabled = true;
    btn.textContent = 'Guardando…';
  }

  try{
    // профиль
    await api(V5 + '/me/profile', { method:'POST', body });  // :contentReference[oaicite:4]{index=4}

    // пароль отдельно
    if (p1){
      await api(V5 + '/me/password', { method:'POST', body:{ password: p1 } }); // :contentReference[oaicite:5]{index=5}
      if (msgPass) msgPass.textContent = 'Contraseña actualizada.';
    }

    if (msgTop) msgTop.textContent = 'Datos guardados.';

    // очистим поля пароля
    const pass1 = document.getElementById('prof-pass1');
    const pass2 = document.getElementById('prof-pass2');
    if (pass1) pass1.value = '';
    if (pass2) pass2.value = '';

  }catch(e){
    if (msgTop) msgTop.textContent = e?.message || 'No se pudo guardar.';
  }finally{
    if (btn){
      btn.disabled = false;
      btn.textContent = 'Guardar cambios';
    }
  }
}


function stripTabParam(urlLike){
  try {
    const x = new URL(urlLike || '/alumno/', location.origin);
    x.searchParams.delete('tab'); // ✅ убираем tab всегда
    const qs = x.searchParams.toString();
    return x.pathname + (qs ? `?${qs}` : '') + (x.hash || '');
  } catch (_) {
    return '/alumno/';
  }
}

function initProfileTabRouting(){
  const u = new URL(location.href);
  const tab = u.searchParams.get('tab') || 'login';

  // ✅ кнопка "Volver" в профиле → назад в /alumno/ (без tab)
document.getElementById('btn-prof-back')?.addEventListener('click', (e) => {
  e.preventDefault();
  e.stopPropagation();
  e.stopImmediatePropagation();   // ✅ убивает другие обработчики на этой же кнопке
  location.assign('/alumno/');    // ✅ всегда на /alumno/ без tab
}, true);                         // ✅ capture: сработает раньше других


  document.getElementById('btn-prof-save')?.addEventListener('click', saveProfile);

  if (tab === 'profile') {
    setTab('profile');
    loadProfile();
  } else {
    setTab('login');
  }
}


  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();

