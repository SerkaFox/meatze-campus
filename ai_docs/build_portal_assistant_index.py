#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOGEN = PROJECT_ROOT / "docs" / "autogen_strict"

PORTAL_MAP = AUTOGEN / "portal_map.json"
ACTION_LINKS = AUTOGEN / "action_links.json"
ROUTER_MAP = AUTOGEN / "router_map.json"

OUT_JSON = AUTOGEN / "assistant_index.json"
OUT_MD = AUTOGEN / "assistant_index.md"


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def path_to_module(py_rel: str) -> str:
    # "api/auth_views.py" -> "api.auth_views"
    p = py_rel.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    return p.replace("/", ".")


def classify_template_key(rel: str) -> Optional[str]:
    p = rel.replace("\\", "/")
    if p.startswith("templates/meatze_admin/") and p.endswith(".html"):
        return f"admin:{Path(p).stem}"
    if p.startswith("templates/panel/") and p.endswith(".html"):
        return f"panel:{Path(p).stem}"
    if p.startswith("templates/") and p.endswith(".html"):
        return f"tpl:{Path(p).stem}"
    return None


def classify_js_key(rel: str) -> Optional[str]:
    p = rel.replace("\\", "/")
    if p.startswith("static/meatze/admin/") and p.endswith(".js"):
        return f"admin:{Path(p).stem}"
    if p.startswith("static/") and p.endswith(".js"):
        return f"js:{Path(p).stem}"
    return None


def uniq_list(xs: List[Any]) -> List[Any]:
    out = []
    seen = set()
    for x in xs:
        k = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def build_view_template_index(router: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Returns map:
      "core.views.admin_panel" -> ["meatze_admin/base_admin.html", ...]
    Strictly from router_map["view_templates"] (render() literals).
    """
    vt = router.get("view_templates") or {}
    idx: Dict[str, List[str]] = {}

    for py_rel, funcs in vt.items():
        mod = path_to_module(py_rel)
        if not isinstance(funcs, dict):
            continue
        for fn_name, tpls in funcs.items():
            if not isinstance(tpls, list):
                continue
            key = f"{mod}.{fn_name}"
            idx[key] = sorted(set([t for t in tpls if isinstance(t, str)]))
    return idx


def map_routes_to_templates(router: Dict[str, Any], view_tpl_idx: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    routes = router.get("routes_flat") or []
    out: List[Dict[str, Any]] = []

    for r in routes:
        if not isinstance(r, dict) or r.get("type") != "route":
            continue
        route = r.get("route")
        view = r.get("view")
        name = r.get("name")
        prefix = r.get("full_prefix") or ""

        tpl_list = view_tpl_idx.get(view, [])
        tpl_keys = [classify_template_key("templates/" + t if not t.startswith("templates/") else t) for t in tpl_list]
        tpl_keys = [k for k in tpl_keys if k]

        out.append({
            "url": f"{prefix}{route}",
            "view": view,
            "name": name,
            "templates": tpl_list,
            "template_keys": uniq_list(tpl_keys),
        })
    return out


def group_actions_by_js_key(actions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by: Dict[str, List[Dict[str, Any]]] = {}
    for a in actions:
        f = a.get("file")
        if not isinstance(f, str):
            continue
        jk = classify_js_key(f)
        if not jk:
            continue
        rec = {
            "selector": a.get("selector"),
            "event": a.get("event"),
            "line": a.get("line"),
            "handlerName": a.get("handlerName"),
            "calls": a.get("calls") or [],
            "endpoints": a.get("endpoints") or [],
            "endpointsTemplates": a.get("endpointsTemplates") or [],
            "selectorHints": a.get("selectorHints") or [],
            "source": a.get("source"),
        }
        by.setdefault(jk, []).append(rec)

    # de-noise duplicates
    for k in list(by.keys()):
        by[k] = uniq_list(by[k])
    return by


def attach_actions_to_pages(portal: Dict[str, Any], actions_by_js: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    pages = portal.get("pages") or {}
    out_pages: Dict[str, Any] = {}

    for page_key, p in pages.items():
        templates = p.get("templates") or []
        scripts = p.get("scripts") or []
        ui = p.get("ui") or {}
        jsfacts = p.get("js") or {}

        # derive script keys and collect actions
        act: List[Dict[str, Any]] = []
        script_keys = []
        for s in scripts:
            sk = classify_js_key(s)
            if sk:
                script_keys.append(sk)
                act.extend(actions_by_js.get(sk, []))

        out_pages[page_key] = {
            "page_key": page_key,
            "templates": templates,
            "scripts": scripts,
            "script_keys": uniq_list(script_keys),
            "ui": {
                "ids": ui.get("ids") or [],
                "classes": ui.get("classes") or [],
            },
            "js": {
                "apiBases": jsfacts.get("apiBases") or {},
                "endpoints": jsfacts.get("endpoints") or [],
                "endpointsTemplates": jsfacts.get("endpointsTemplates") or [],
                "endpointsParts": jsfacts.get("endpointsParts") or [],
                "domSelectors": jsfacts.get("domSelectors") or [],
                "events": jsfacts.get("events") or [],
                "functions": jsfacts.get("functions") or [],
                "globals": jsfacts.get("globals") or [],
            },
            "actions": act,
        }

    return out_pages


def build_templatekey_to_pages(pages: Dict[str, Any]) -> Dict[str, List[str]]:
    m: Dict[str, List[str]] = {}
    for pk, p in pages.items():
        for t in p.get("templates") or []:
            tk = classify_template_key(t)
            if tk:
                m.setdefault(tk, []).append(pk)
    for k in list(m.keys()):
        m[k] = sorted(set(m[k]))
    return m


def join_routes_with_pages(routes: List[Dict[str, Any]], templatekey_to_pages: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in routes:
        tks = r.get("template_keys") or []
        page_keys: List[str] = []
        for tk in tks:
            page_keys.extend(templatekey_to_pages.get(tk, []))
        out.append({
            **r,
            "page_keys": sorted(set(page_keys)),
        })
    return out


def to_markdown(index: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Assistant Index (strict)\n")
    lines.append("Este archivo es un índice consolidado para el asistente. No contiene inferencias: sólo hechos extraídos.\n")

    routes = index.get("routes") or []
    pages = index.get("pages") or {}

    lines.append("## Routes\n")
    for r in routes[:120]:
        url = r.get("url")
        view = r.get("view")
        name = r.get("name")
        tpls = r.get("templates") or []
        pks = r.get("page_keys") or []
        lines.append(f"- `{url}` → `{view}`" + (f" (name=`{name}`)" if name else ""))
        if tpls:
            lines.append(f"  - templates: {', '.join([f'`{t}`' for t in tpls])}")
        if pks:
            lines.append(f"  - page_keys: {', '.join([f'`{k}`' for k in pks])}")
    if len(routes) > 120:
        lines.append(f"\n- ... ({len(routes)-120} más)\n")

    lines.append("\n## Pages\n")
    for pk in sorted(pages.keys())[:80]:
        p = pages[pk]
        lines.append(f"### {pk}")
        lines.append(f"- templates: {len(p.get('templates') or [])}")
        lines.append(f"- scripts: {len(p.get('scripts') or [])}")
        lines.append(f"- ui.ids: {len((p.get('ui') or {}).get('ids') or [])}")
        lines.append(f"- ui.classes: {len((p.get('ui') or {}).get('classes') or [])}")
        lines.append(f"- actions: {len(p.get('actions') or [])}")

        # show a compact action preview
        acts = p.get("actions") or []
        for a in acts[:6]:
            ev = a.get("event")
            sel = a.get("selector") or "(unknown selector)"
            eps_t = a.get("endpointsTemplates") or []
            lines.append(f"  - {ev} on `{sel}`" + (f" → {eps_t[0]}" if eps_t else ""))
        if len(acts) > 6:
            lines.append(f"  - ... (+{len(acts)-6})")
        lines.append("")
    if len(pages) > 80:
        lines.append(f"\n- ... ({len(pages)-80} páginas más)\n")

    return "\n".join(lines)


def main() -> None:
    portal = read_json(PORTAL_MAP)
    actions_raw = read_json(ACTION_LINKS).get("actions") or []
    router = read_json(ROUTER_MAP)

    view_tpl_idx = build_view_template_index(router)
    routes = map_routes_to_templates(router, view_tpl_idx)

    actions_by_js = group_actions_by_js_key(actions_raw)
    pages = attach_actions_to_pages(portal, actions_by_js)

    templatekey_to_pages = build_templatekey_to_pages(pages)
    routes_joined = join_routes_with_pages(routes, templatekey_to_pages)

    index = {
        "meta": {
            "generated_from": {
                "portal_map": str(PORTAL_MAP),
                "action_links": str(ACTION_LINKS),
                "router_map": str(ROUTER_MAP),
            }
        },
        "routes": routes_joined,
        "pages": pages,
        "view_template_index": view_tpl_idx,   # strict: view -> templates from render()
        "templatekey_to_pages": templatekey_to_pages,
    }

    AUTOGEN.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(to_markdown(index), encoding="utf-8")

    print(f"[OK] {OUT_JSON}")
    print(f"[OK] {OUT_MD}")


if __name__ == "__main__":
    main()
