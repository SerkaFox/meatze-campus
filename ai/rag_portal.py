# ai/rag_portal.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from django.conf import settings


DEFAULT_INDEX_PATH = "docs/autogen_strict/assistant_index.json"
SYNONYMS = {
    "чат": ["chat", "mensajes", "mensaje", "conversación"],
    "сообщения": ["mensajes", "message", "chat"],
    "календарь": ["calendario", "agenda"],
    "расписание": ["horario", "horarios", "calendario"],
    "войти": ["acceder", "entrar", "login", "iniciar", "sesión"],
    "вход": ["acceder", "entrar", "login", "iniciar", "sesión"],
    "пароль": ["contraseña", "password"],
    "почта": ["correo", "email", "e-mail"],
    "учитель": ["docente", "teacher", "profesor"],
    "админ": ["admin", "administración", "administrador"],
    "ia": ["inteligencia", "ai", "assistant", "asistente"],
    "chat": ["chat", "mensajes", "mensaje", "conversacion", "conversación"],
    "¿hay": ["existe", "tiene"],   # опционально

}


@dataclass
class PortalHit:
    score: float
    kind: str        # "route" | "page"
    key: str         # url or page_key
    text: str        # compact context chunk


def _load_index() -> Dict[str, Any]:
    p = Path(getattr(settings, "MEATZE_ASSISTANT_INDEX_PATH", DEFAULT_INDEX_PATH))
    if not p.is_absolute():
        p = Path(settings.BASE_DIR) / p
    data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    return data


def _tokenize(q: str) -> List[str]:
    q = (q or "").lower()
    q = re.sub(r"[^a-z0-9áéíóúüñ/#:_\- ]+", " ", q, flags=re.I)
    toks = [t for t in q.split() if len(t) >= 2]

    # expand with synonyms (strict, deterministic)
    expanded = list(toks)
    for t in toks:
        for syn in SYNONYMS.get(t, []):
            expanded.append(syn.lower())

    # uniq preserving order
    seen = set()
    out = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            out.append(t)

    return out[:120]



def _score_text(tokens: List[str], text: str) -> float:
    t = (text or "").lower()
    score = 0.0
    for tok in tokens:
        if tok in t:
            score += 1.0
    # extra boost for IA tab
    ia_intent = ("ia" in tokens) or ("inteligencia" in tokens)
    if ia_intent and ("tabs/ia" in t or " ia " in f" {t} "):
        score += 2.0

    # небольшой бонус за “login/access” intents
    boost_words = ("acceder", "entrar", "login", "iniciar", "sesión", "pin", "correo", "contraseña", "campus")
    for w in boost_words:
        if w in t:
            score += 0.2
    # extra boost if question likely asks about chat
    chat_intent = ("chat" in tokens) or ("чат" in tokens)
    if chat_intent and ("chat" in t or "mensajes" in t):
        score += 2.0

    return score


def _compact_page(page: Dict[str, Any]) -> str:
    ui = page.get("ui") or {}
    ids_ = ui.get("ids") or []
    actions = page.get("actions") or []
    js = page.get("js") or {}
    eps_t = js.get("endpointsTemplates") or []

    # покажем только самое полезное, чтобы контекст был короткий и точный
    lines = []
    lines.append(f"PAGE {page.get('page_key')}")
    if page.get("templates"):
        lines.append(f"templates: {', '.join(page['templates'][:3])}")
    if page.get("scripts"):
        lines.append(f"scripts: {', '.join(page['scripts'][:3])}")
    if ids_:
        lines.append("ui.ids: " + ", ".join(ids_[:25]) + ("" if len(ids_) <= 25 else f" ...(+{len(ids_)-25})"))
    if actions:
        # покажем 6 действий
        for a in actions[:6]:
            ev = a.get("event")
            sel = a.get("selector") or "(unknown selector)"
            et = (a.get("endpointsTemplates") or [])
            lines.append(f"action: {ev} on {sel}" + (f" -> {et[0]}" if et else ""))
        if len(actions) > 6:
            lines.append(f"actions_more: +{len(actions)-6}")
    if eps_t:
        lines.append("js.endpointsTemplates: " + ", ".join(eps_t[:6]) + ("" if len(eps_t) <= 6 else " ..."))
    return "\n".join(lines)


def _compact_route(r: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"ROUTE {r.get('url')} -> {r.get('view')}")
    tpls = r.get("templates") or []
    pks = r.get("page_keys") or []
    if tpls:
        lines.append("templates: " + ", ".join(tpls[:3]) + ("" if len(tpls) <= 3 else " ..."))
    if pks:
        lines.append("page_keys: " + ", ".join(pks[:6]) + ("" if len(pks) <= 6 else " ..."))
    return "\n".join(lines)


def retrieve_portal_context(question: str, role: str = "visitor", top_k: int = 6) -> Tuple[str, List[PortalHit]]:
    """
    Возвращает (context_text, hits).
    Строго: контекст строится только из assistant_index.json.
    """
    idx = _load_index()
    tokens = _tokenize(question)

    hits: List[PortalHit] = []

    # routes
    for r in idx.get("routes") or []:
        txt = _compact_route(r)
        s = _score_text(tokens, txt)
        if s > 0:
            hits.append(PortalHit(score=s, kind="route", key=str(r.get("url")), text=txt))

    # pages
    pages = idx.get("pages") or {}
    for pk, page in pages.items():
        txt = _compact_page(page)
        s = _score_text(tokens, txt)
        if s > 0:
            hits.append(PortalHit(score=s, kind="page", key=str(pk), text=txt))

    # жесткий буст по роли: admin -> admin:* страницы, alumno -> panel:* и т.д.
    if role == "admin":
        for h in hits:
            if h.kind == "page" and str(h.key).startswith("admin:"):
                h.score += 1.0
    elif role in ("alumno", "docente"):
        for h in hits:
            if h.kind == "page" and str(h.key).startswith("panel:"):
                h.score += 0.5

    hits.sort(key=lambda x: x.score, reverse=True)
    hits = hits[:top_k]

    ctx = "\n\n".join(h.text for h in hits)
    return ctx, hits
