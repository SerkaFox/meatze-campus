(function(){
  'use strict';

  // =========================
  // CONFIG
  // =========================
  const CAP_MS = 120000;              // idle cap for analytics heartbeat
  const HB_ACTIVE_MS = 8000;          // attendance hb when visible
  const HB_BG_MS = 45000;             // attendance hb when hidden (best-effort)
  const REQ_THROTTLE_MS = 60000;      // don't spam request
  const DEBUG = !!(window.MZ_TRAFFIC && window.MZ_TRAFFIC.debug);

  const V5 = (window.MEATZE && window.MEATZE.V5)
    ? window.MEATZE.V5.replace(/\/$/, '')
    : (location.origin.replace(/\/$/, '') + '/meatze/v5');

  const ENDPOINT = (window.MZ_TRAFFIC && window.MZ_TRAFFIC.endpoint)
    ? String(window.MZ_TRAFFIC.endpoint)
    : (V5 + '/event');

  const IS_COURSE_PAGE = location.pathname.startsWith('/alumno/curso/');

  let CURSO = (window.MZ_TRAFFIC && window.MZ_TRAFFIC.curso) ? String(window.MZ_TRAFFIC.curso) : "";
  if (!CURSO) {
    const m = location.pathname.match(/^\/alumno\/curso\/([^\/]+)/);
    if (m && m[1]) CURSO = m[1];
  }

  function log(){
    if (!DEBUG) return;
    try { console.log.apply(console, arguments); } catch(_){}
  }
  function warn(){
    if (!DEBUG) return;
    try { console.warn.apply(console, arguments); } catch(_){}
  }

  log("[ATT:init]", { IS_COURSE_PAGE, CURSO, path: location.pathname, V5, ENDPOINT });

  // =========================
  // helpers
  // =========================
  function sid(){
    let v = sessionStorage.getItem("mz_sid");
    if(!v){
      v = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random());
      sessionStorage.setItem("mz_sid", v);
    }
    return v;
  }

  function nextSeq(){
    const k="mz_seq";
    const n = (parseInt(sessionStorage.getItem(k)||"0",10)+1);
    sessionStorage.setItem(k, String(n));
    return n;
  }

  async function safeFetch(url, opt){
    try{
      const r = await fetch(url, opt);
      if (!r.ok) warn("[ATT:http]", url, r.status);
      return r;
    }catch(e){
      warn("[ATT:net]", url, e && e.message);
      return null;
    }
  }

  function post(ev, payload){
    const body = Object.assign({
      event: ev,
      session_id: sid(),
      seq: nextSeq(),
      page: location.pathname,
      ref: document.referrer || "",
      ts: Date.now(),
      curso_codigo: CURSO,
      vis: document.hidden ? "hidden" : "visible",
    }, payload||{});

    // keepalive helps for "pagehide"/unload type sends
    return safeFetch(ENDPOINT,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      credentials:"include",
      keepalive: true,
      body: JSON.stringify(body)
    });
  }

  window.mzTrack = post;

  // =========================
  // page_view (once)
  // =========================
  post("page_view", { meta: { tag: (window.MZ_TRAFFIC && window.MZ_TRAFFIC.page) || "" } });

  // =========================
  // Attendance
  // =========================
  const REQ_URL = V5 + '/attendance/request';
  const HB_URL  = V5 + '/attendance/heartbeat';

  let hbTimer = null;
  let lastHbAt = 0;

  function hbIntervalMs(){
    return document.hidden ? HB_BG_MS : HB_ACTIVE_MS;
  }

  function canDoAttendance(){
    return !!(IS_COURSE_PAGE && CURSO);
  }

  async function sendAttendanceRequest(force){
    if (!canDoAttendance()) return;

    const kLast = `mz_att_req_last::${CURSO}`;
    const last = parseInt(sessionStorage.getItem(kLast)||"0", 10) || 0;
    const now = Date.now();

    if (!force && (now - last) < REQ_THROTTLE_MS){
      return;
    }
    sessionStorage.setItem(kLast, String(now));

    log("[ATT:req] sending", { CURSO, force });

    await safeFetch(REQ_URL, {
      method:'POST',
      credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ curso_codigo: CURSO, session_id: sid() })
    });
  }

  async function sendAttendanceHeartbeat(reason){
    if (!canDoAttendance()) return;

    // watchdog: if browser was sleeping, we'll send immediately on resume
    lastHbAt = Date.now();
    log("[ATT:hb] sending", { CURSO, reason, hidden: document.hidden });

    await safeFetch(HB_URL, {
      method:'POST',
      credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ curso_codigo: CURSO, session_id: sid() })
    });
  }

  function stopHb(){
    if (hbTimer){
      clearTimeout(hbTimer);
      hbTimer = null;
    }
  }

  function scheduleHb(reason){
    stopHb();
    if (!canDoAttendance()) return;

    const ms = hbIntervalMs();
    hbTimer = setTimeout(async function tick(){
      await sendAttendanceHeartbeat(reason || "timer");
      scheduleHb("timer");
    }, ms);
  }

  // Start attendance loop
  if (canDoAttendance()){
    // make sure a session exists
    sendAttendanceRequest(false);
    // first heartbeat quickly (helps teacher see it right aways)
    sendAttendanceHeartbeat("init");
    scheduleHb("init");
  }

  // When tab becomes visible again: re-request + immediate hb
  document.addEventListener('visibilitychange', function(){
    if (!canDoAttendance()) return;

    if (!document.hidden){
      // coming back to foreground
      sendAttendanceRequest(true);
      sendAttendanceHeartbeat("visibility");
    }
    scheduleHb("visibilitychange");
  }, {passive:true});

  // BFCache restore / back-forward navigation
  window.addEventListener('pageshow', function(ev){
    if (!canDoAttendance()) return;

    // even if persisted, timers can be stale
    sendAttendanceRequest(true);
    sendAttendanceHeartbeat(ev && ev.persisted ? "pageshow_bfcache" : "pageshow");
    scheduleHb("pageshow");
  });

  // Before leaving: best-effort final ping
  window.addEventListener('pagehide', function(){
    if (!canDoAttendance()) return;
    // keepalive should allow the request to be sent
    sendAttendanceHeartbeat("pagehide");
  }, {passive:true});

  // =========================
  // Analytics heartbeat (activity-based)
  // =========================
  let lastAct = Date.now();
  ["mousemove","keydown","scroll","touchstart"].forEach(evt=>{
    window.addEventListener(evt, ()=>{ lastAct = Date.now(); }, {passive:true});
  });

  // send a "ping" when user returns (optional)
  window.addEventListener('focus', ()=>{ lastAct = Date.now(); }, {passive:true});

  setInterval(()=>{
    // don't spam analytics in background
    if (document.hidden) return;

    const idle = Date.now() - lastAct;
    if (idle <= CAP_MS){
      post("heartbeat", {});
    }
  }, 10000); // 10s is enough; 5s is noisy

})();
