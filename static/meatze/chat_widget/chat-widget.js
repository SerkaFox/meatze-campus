(() => {
  const $ = (s) => document.querySelector(s);

  const fab = $("#mz-chat-fab");
  const panel = $("#mz-chat-panel");
  const closeBtn = $("#mz-chat-close");
  const backdrop = $("#mz-chat-backdrop");
  const body = $("#mz-chat-body");
  const input = $("#mz-chat-input");
  const send = $("#mz-chat-send");

  if (!fab || !panel || !body || !input || !send) return;

  const AVA_ANA = "/static/meatze/avatars/ana.png";
  const AVA_CARLOS = "/static/meatze/avatars/carlos.png";


function openChat() {
  panel.classList.add("is-open");
  backdrop.classList.add("is-open");

  panel.removeAttribute("aria-hidden");
  backdrop.removeAttribute("aria-hidden");

  // inert OFF
  panel.inert = false;
  backdrop.inert = false;

  // фокус в инпут
  setTimeout(() => input.focus(), 50);
}

function closeChat() {
  // 1) если фокус внутри панели — уводим его наружу (на FAB)
  if (panel.contains(document.activeElement)) {
    fab.focus();
  }

  // 2) inert ON (запрещает фокус/клики внутри)
  panel.inert = true;
  backdrop.inert = true;

  // 3) теперь можно скрывать от AT
  panel.setAttribute("aria-hidden", "true");
  backdrop.setAttribute("aria-hidden", "true");

  panel.classList.remove("is-open");
  backdrop.classList.remove("is-open");
}


  fab.addEventListener("click", openChat);
  closeBtn?.addEventListener("click", closeChat);
  backdrop?.addEventListener("click", closeChat);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeChat();
  });

function escapeHTML(s) {
  return (s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function linkifyDOM(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html || "";

  const urlRe = /(\bhttps?:\/\/[^\s<]+|\bwww\.[^\s<]+)/gi;

  const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_TEXT, null);

  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  for (const node of textNodes) {
    const txt = node.nodeValue;
    if (!txt || !urlRe.test(txt)) continue;

    urlRe.lastIndex = 0;

    const frag = document.createDocumentFragment();
    let last = 0;
    let m;

    while ((m = urlRe.exec(txt))) {
      const raw = m[0];
      const start = m.index;
      const end = start + raw.length;

      // текст до ссылки
      if (start > last) frag.appendChild(document.createTextNode(txt.slice(last, start)));

      // чистим хвостовую пунктуацию типа . , ) ! ?
      let clean = raw.replace(/[.,!?;:)"'`]+$/, "");
      const tail = raw.slice(clean.length);

      const href = clean.startsWith("www.") ? "https://" + clean : clean;

      const a = document.createElement("a");
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = clean;

      frag.appendChild(a);
      if (tail) frag.appendChild(document.createTextNode(tail));

      last = end;
    }

    // остаток
    if (last < txt.length) frag.appendChild(document.createTextNode(txt.slice(last)));

    node.replaceWith(frag);
  }

  return tpl.innerHTML;
}

function sanitizeBotHTML(html) {
  // Разрешаем только: <a href> и <br>
  const tpl = document.createElement("template");
  tpl.innerHTML = html || "";

  const allowedTags = new Set(["A", "BR"]);

  const walk = (node) => {
    // чистим детей сначала
    [...node.childNodes].forEach((child) => {
      if (child.nodeType === Node.ELEMENT_NODE) {
        const tag = child.tagName;

        if (!allowedTags.has(tag)) {
          // заменяем запрещённый тег на его текстовое содержимое (без потери текста)
          const text = document.createTextNode(child.textContent || "");
          child.replaceWith(text);
          return;
        }

        if (tag === "A") {
          // оставляем только href
          const href = child.getAttribute("href") || "";
          // базовая защита от javascript:
          const safeHref = href.trim().toLowerCase().startsWith("javascript:")
            ? "#"
            : href;

          // очищаем все атрибуты
          [...child.attributes].forEach((a) => child.removeAttribute(a.name));

          child.setAttribute("href", safeHref);
          child.setAttribute("target", "_blank");
          child.setAttribute("rel", "noopener noreferrer");
        }
      }
      walk(child);
    });
  };

  walk(tpl.content);
  return tpl.innerHTML;
}

function formatBotMessage(text) {
  const t = (text || "").trim();
  if (!t) return "";

  // 1) Если пришёл HTML (<a ...>) — санитайзим
  if (/<a\s/i.test(t)) {
    const withBr = t.replace(/\r\n|\r|\n/g, "<br>");
    return sanitizeBotHTML(withBr);
  }

  // 2) Обычный текст: escape + <br>
  let safe = escapeHTML(t).replace(/\r\n|\r|\n/g, "<br>");

  // 3) Markdown links: [label](url)
  safe = safe.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)<]+)\)/g,
    (_, label, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`
  );

  // 4) Авто-линковка всех https:// и www. (надёжно, через DOM)
  safe = linkifyDOM(safe);

  return safe;
}




  function appendUser(text) {
    const row = document.createElement("div");
    row.className = "mz-msg user";
    row.innerHTML = `
      <div class="mz-bubble">
        <div class="mz-name">TÚ</div>
        <div class="mz-text"></div>
      </div>
    `;
    row.querySelector(".mz-text").innerHTML = formatBotMessage(text);
    body.appendChild(row);
    body.scrollTop = body.scrollHeight;
  }
  
  

function appendBot(name, avatar, text) {
  const row = document.createElement("div");
  row.className = "mz-msg bot";
  row.dataset.bot = name; // для CSS

  row.innerHTML = `
    <div class="ava"><img src="${avatar}" alt="${name}"></div>
    <div class="mz-bubble">
      <div class="mz-name">${name}</div>
      <div class="mz-text"></div>
    </div>
  `;

  const html = formatBotMessage(text);

  row.querySelector(".mz-text").innerHTML =
    html.replace(
      /<a([^>]+href="https:\/\/meatzeaula\.es\/"[^>]*)>(.*?)<\/a>/gi,
      `<a$1 class="mz-link-btn">$2</a>`
    );

  body.appendChild(row);
  body.scrollTop = body.scrollHeight;
}


  function renderDuoAnswer(answer) {
    const t = (answer || "").trim();
    if (!t) return;

    // Если ответ уже в формате:
    // ANA: ...
    // CARLOS: ...
    const parts = t.split(/\n\s*\n/).map(x => x.trim()).filter(Boolean);
    if (parts.length >= 2 && parts[0].startsWith("ANA:") && parts[1].startsWith("CARLOS:")) {
      appendBot("ANA", AVA_ANA, parts[0].replace(/^ANA:\s*/, ""));
      appendBot("CARLOS", AVA_CARLOS, parts[1].replace(/^CARLOS:\s*/, ""));
      return;
    }

    // Если один персонаж
    if (t.startsWith("ANA:")) return appendBot("ANA", AVA_ANA, t.replace(/^ANA:\s*/, ""));
    if (t.startsWith("CARLOS:")) return appendBot("CARLOS", AVA_CARLOS, t.replace(/^CARLOS:\s*/, ""));

    // Иначе — как общий бот
    appendBot("MEATZE", AVA_ANA, t);
  }
  

  async function sendMsg() {
    const text = input.value.trim();
    if (!text) return;
  // addressed: кому адресован ответ (ANA / CARLOS / all). Если у тебя нет селектора — будет "all".
	const addressed =
	  (window.MZChatState && window.MZChatState.addressed) ||
	  document.querySelector('[name="mz-addressed"]:checked')?.value ||
	  "all";
    input.value = "";
    appendUser(text);
    send.disabled = true;

    // роль можно передавать с твоей страницы, если у тебя есть window.MEATZE_ROLE
    const role = (window.MEATZE_ROLE || "visitor");

    try {
      const r = await fetch("/meatze/v5/ai/help", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, role, duo: true })
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.msg || j?.error || "HTTP " + r.status);
      renderDuoAnswer(j.answer);
    } catch (e) {
      appendBot("MEATZE", AVA_ANA, "Ahora mismo no puedo responder. Inténtalo de nuevo.");
      console.error(e);
    } finally {
      send.disabled = false;
      body.scrollTop = body.scrollHeight;
    }
  }

  send.addEventListener("click", sendMsg);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMsg();
  });

  // Приветственное сообщение (1 раз за сессию)
  if (!sessionStorage.getItem("mz_chat_hello")) {
    appendBot("ANA", AVA_ANA, "Hola 🙂 Soy ANA. Pregúntame cómo entrar, ver calendario, materiales o chat.");
    appendBot("CARLOS", AVA_CARLOS, "Y yo soy CARLOS. Si algo falla (PIN, acceso, errores), lo revisamos.");
    sessionStorage.setItem("mz_chat_hello", "1");
  }
})();
