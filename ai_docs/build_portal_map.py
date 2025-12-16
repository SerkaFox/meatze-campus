#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception as e:
                raise RuntimeError(f"JSONL inválido en {path}:{line_no}: {e}")
    return items


def norm_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def merge_unique(dst: List[Any], src: List[Any]) -> List[Any]:
    seen = set()
    out = []
    for x in dst + src:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def classify_template(path: str) -> Optional[str]:
    # page_key = (meatze_admin/horarios.html) -> "admin:horarios"
    p = path.replace("\\", "/")
    if p.startswith("templates/meatze_admin/") and p.endswith(".html"):
        name = Path(p).stem
        return f"admin:{name}"
    if p.startswith("templates/panel/") and p.endswith(".html"):
        name = Path(p).stem
        return f"panel:{name}"
    if p.startswith("templates/") and p.endswith(".html"):
        name = Path(p).stem
        return f"tpl:{name}"
    return None


def classify_static_js(path: str) -> Optional[str]:
    p = path.replace("\\", "/")
    if p.startswith("static/meatze/admin/") and p.endswith(".js"):
        name = Path(p).stem
        return f"admin:{name}"
    if p.startswith("static/") and p.endswith(".js"):
        name = Path(p).stem
        return f"js:{name}"
    return None


def make_entry(key: str) -> Dict[str, Any]:
    return {
        "key": key,
        "templates": [],  # html paths
        "scripts": [],    # js paths
        "python": [],     # py paths
        "ui": {
            "ids": [],
            "classes": [],
        },
        "js": {
            "apiBases": {},
            "endpoints": [],
            "endpointsTemplates": [],
            "endpointsParts": [],
            "domSelectors": [],
            "events": [],
            "functions": [],
            "globals": [],
        },
        "py": {
            "endpoints": [],
            "functions": [],
            "classes": [],
        }
    }


def merge_dict_shallow(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    # only for apiBases: keep latest value per key, but stable
    out = dict(dst)
    for k, v in (src or {}).items():
        if k not in out:
            out[k] = v
        else:
            # if already set, keep the longer/more informative representation
            if isinstance(v, str) and isinstance(out[k], str) and len(v) > len(out[k]):
                out[k] = v
    return out


def build_portal_map(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    pages: Dict[str, Dict[str, Any]] = {}
    misc: Dict[str, Any] = {"unmapped": {"html": [], "js": [], "python": [], "other": []}}

    def get_page(key: str) -> Dict[str, Any]:
        if key not in pages:
            pages[key] = make_entry(key)
        return pages[key]

    for it in items:
        rel = (it.get("path") or "").replace("\\", "/")
        typ = it.get("type") or ""

        # --- HTML
        if typ == "html":
            k = classify_template(rel)
            if not k:
                misc["unmapped"]["html"].append(rel)
                continue
            page = get_page(k)
            page["templates"] = merge_unique(page["templates"], [rel])

            # ids/classes may or may not exist depending on your facts writer
            ids_ = norm_list(it.get("ids"))
            cls_ = norm_list(it.get("classes"))
            page["ui"]["ids"] = merge_unique(page["ui"]["ids"], ids_)
            page["ui"]["classes"] = merge_unique(page["ui"]["classes"], cls_)
            continue

        # --- JS
        if typ == "js":
            k = classify_static_js(rel)
            if not k:
                misc["unmapped"]["js"].append(rel)
                continue
            page = get_page(k)
            page["scripts"] = merge_unique(page["scripts"], [rel])

            page["js"]["apiBases"] = merge_dict_shallow(page["js"]["apiBases"], it.get("apiBases") or {})
            page["js"]["endpoints"] = merge_unique(page["js"]["endpoints"], norm_list(it.get("endpoints")))
            page["js"]["endpointsTemplates"] = merge_unique(page["js"]["endpointsTemplates"], norm_list(it.get("endpointsTemplates")))
            page["js"]["endpointsParts"] = merge_unique(page["js"]["endpointsParts"], norm_list(it.get("endpointsParts")))
            page["js"]["domSelectors"] = merge_unique(page["js"]["domSelectors"], norm_list(it.get("domSelectors")))
            page["js"]["events"] = merge_unique(page["js"]["events"], norm_list(it.get("events")))
            page["js"]["functions"] = merge_unique(page["js"]["functions"], norm_list(it.get("functions")))
            page["js"]["globals"] = merge_unique(page["js"]["globals"], norm_list(it.get("globals")))
            continue

        # --- PY
        if typ == "python":
            # python файлы не мапим к "странице" по умолчанию, но можно складывать в общую секцию
            # (позже свяжем urls.py → views → templates)
            misc["unmapped"]["python"].append(rel)
            continue

        misc["unmapped"]["other"].append(rel)

    # secondary join: if we have admin:horarios template AND admin:horarios js, keep as same key (already same)
    # But sometimes template key "admin:horarios" and script key "admin:horarios" exist independently; ensure merged.
    # (In our logic they already share key if names match.)

    return {"pages": pages, "misc": misc}


def to_markdown(portal: Dict[str, Any]) -> str:
    pages = portal["pages"]
    lines: List[str] = []
    lines.append("# Portal Map (strict, desde facts.jsonl)\n")

    for key in sorted(pages.keys()):
        p = pages[key]
        lines.append(f"## {key}\n")

        if p["templates"]:
            lines.append("### Templates")
            for t in p["templates"]:
                lines.append(f"- {t}")
        else:
            lines.append("### Templates")
            lines.append("- (ninguno)")

        if p["scripts"]:
            lines.append("\n### Scripts")
            for s in p["scripts"]:
                lines.append(f"- {s}")
        else:
            lines.append("\n### Scripts")
            lines.append("- (ninguno)")

        # UI
        lines.append("\n### UI (HTML)")
        ids_ = p["ui"]["ids"]
        cls_ = p["ui"]["classes"]
        lines.append(f"- ids: {len(ids_)}")
        if ids_:
            lines.append("  - " + "\n  - ".join(map(str, ids_[:80])) + ("" if len(ids_) <= 80 else f"\n  - ... ({len(ids_)-80} más)"))
        lines.append(f"- classes: {len(cls_)}")
        if cls_:
            lines.append("  - " + "\n  - ".join(map(str, cls_[:80])) + ("" if len(cls_) <= 80 else f"\n  - ... ({len(cls_)-80} más)"))

        # JS
        j = p["js"]
        lines.append("\n### JS (facts)")
        if j["apiBases"]:
            lines.append("- apiBases:")
            for k in sorted(j["apiBases"].keys()):
                lines.append(f"  - {k} = {j['apiBases'][k]}")
        else:
            lines.append("- apiBases: (ninguna)")

        for title, field in [
            ("endpoints (literales)", "endpoints"),
            ("endpoints (templates)", "endpointsTemplates"),
            ("endpoints (parts)", "endpointsParts"),
            ("domSelectors", "domSelectors"),
            ("events", "events"),
        ]:
            arr = j[field]
            lines.append(f"- {title}: {len(arr)}")
            if arr:
                lines.append("  - " + "\n  - ".join(map(str, arr[:60])) + ("" if len(arr) <= 60 else f"\n  - ... ({len(arr)-60} más)"))

        # functions: too big – show count + top 40 names if available
        funcs = j["functions"]
        lines.append(f"- functions: {len(funcs)}")
        if funcs:
            names = []
            for f in funcs:
                if isinstance(f, dict) and f.get("name"):
                    names.append(f.get("name"))
            names = [n for n in names if n]
            if names:
                uniq = []
                seen = set()
                for n in names:
                    if n not in seen:
                        seen.add(n)
                        uniq.append(n)
                lines.append("  - " + ", ".join(uniq[:50]) + ("" if len(uniq) <= 50 else f", ... (+{len(uniq)-50})"))

        lines.append("")  # spacer

    # unmapped summary
    lines.append("\n## Unmapped\n")
    misc = portal.get("misc", {}).get("unmapped", {})
    for k in ["html", "js", "python", "other"]:
        arr = misc.get(k, [])
        lines.append(f"- {k}: {len(arr)}")
        if arr:
            lines.append("  - " + "\n  - ".join(arr[:30]) + ("" if len(arr) <= 30 else f"\n  - ... ({len(arr)-30} más)"))
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default="docs/autogen_strict/facts.jsonl", help="Ruta a facts.jsonl")
    ap.add_argument("--out-json", default="docs/autogen_strict/portal_map.json", help="Salida JSON")
    ap.add_argument("--out-md", default="docs/autogen_strict/portal_map.md", help="Salida MD")
    args = ap.parse_args()

    facts_path = Path(args.facts)
    portal = build_portal_map(load_jsonl(facts_path))

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(portal, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(to_markdown(portal), encoding="utf-8")

    print(f"[OK] portal_map.json -> {out_json}")
    print(f"[OK] portal_map.md   -> {out_md}")


if __name__ == "__main__":
    main()
