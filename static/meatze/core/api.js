/* static/meatze/core/api.js */
(() => {
  'use strict';

  function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }

  async function apiFetch(url, opt = {}) {
    const options = { ...opt };
    options.method = (options.method || 'GET').toUpperCase();

    const headers = new Headers(options.headers || {});
    const isSameOrigin = (() => {
      try { return new URL(url, location.href).origin === location.origin; }
      catch { return true; }
    })();

    if (!options.credentials) options.credentials = 'same-origin';

    const needsCsrf = !['GET','HEAD','OPTIONS','TRACE'].includes(options.method);
    if (isSameOrigin && needsCsrf && !headers.has('X-CSRFToken')) {
      const token = getCookie('csrftoken');
      if (token) headers.set('X-CSRFToken', token);
    }

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      if (!headers.has('Content-Type')) headers.set('Content-Type','application/json');
      options.body = JSON.stringify(options.body);
    }

    if (!headers.has('Accept')) headers.set('Accept','application/json');

    options.headers = headers;

    const res = await fetch(url, options);

    const ct = res.headers.get('content-type') || '';
    const isJson = ct.includes('application/json');
    const data = isJson ? await res.json().catch(()=>null) : await res.text().catch(()=>null);

    if (!res.ok) {
      const err = new Error((data && data.detail) ? data.detail : `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  window.mzApi = window.mzApi || {};
  window.mzApi.fetch = apiFetch;
})();


