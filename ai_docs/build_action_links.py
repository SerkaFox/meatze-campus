#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOGEN = PROJECT_ROOT / "docs" / "autogen_strict"

ACTION_JSON = AUTOGEN / "action_links.json"
ACTION_MD = AUTOGEN / "action_links.md"

# We will analyze only JS in static/
JS_ROOT = PROJECT_ROOT / "static"

NODE_SCRIPT = PROJECT_ROOT / "ai_docs" / "js_action_links_acorn.mjs"


def run_node(js_file: Path) -> Optional[Dict[str, Any]]:
    import subprocess
    try:
        out = subprocess.check_output(
            ["node", str(NODE_SCRIPT), str(js_file)],
            stderr=subprocess.STDOUT,
            text=True
        )
        return json.loads(out)
    except subprocess.CalledProcessError as e:
        print(f"[WARN] JS parse failed: {js_file}: {e.output[:300]}")
    except Exception as e:
        print(f"[WARN] JS parse failed: {js_file}: {e}")
    return None


def scan_js_files() -> List[Path]:
    files: List[Path] = []
    if not JS_ROOT.exists():
        return files
    for p in JS_ROOT.rglob("*.js"):
        # skip vendor/minified if any (optional)
        if p.name.endswith(".min.js"):
            continue
        files.append(p)
    return sorted(files)


def to_markdown(actions: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# Action Links (strict, extracted from JS AST)\n")
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for a in actions:
        by_file.setdefault(a["file"], []).append(a)

    for file in sorted(by_file.keys()):
        lines.append(f"## {file}\n")
        arr = by_file[file]
        if not arr:
            lines.append("- (no actions)\n")
            continue

        # group by selector + event
        arr = sorted(arr, key=lambda x: (x.get("selector") or "", x.get("event") or "", x.get("line") or 0))
        for a in arr[:400]:
            sel = a.get("selector") or "(unknown selector)"
            ev = a.get("event") or "(unknown event)"
            line = a.get("line")
            calls = a.get("calls") or []
            endpoints = a.get("endpoints") or []
            endpoints_t = a.get("endpointsTemplates") or []

            lines.append(f"- **{ev}** on `{sel}` (line {line})")
            if a.get("handlerName"):
                lines.append(f"  - handlerName: `{a['handlerName']}`")
            hints = a.get("selectorHints") or []
            if hints:
                lines.append("  - selectorHints:")
                for h in hints[:10]:
                    lines.append(f"    - `{h}`")
            if calls:
                lines.append(f"  - calls: {', '.join(calls[:12])}" + ("" if len(calls) <= 12 else f" ... (+{len(calls)-12})"))
            if endpoints:
                lines.append("  - endpoints (literal):")
                for e in endpoints[:10]:
                    lines.append(f"    - `{e}`")
            if endpoints_t:
                lines.append("  - endpoints (template/raw):")
                for t in endpoints_t[:8]:
                    lines.append(f"    - `{t}`")
        if len(arr) > 400:
            lines.append(f"\n- ... ({len(arr)-400} más)\n")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    # Ensure the node script exists
    if not NODE_SCRIPT.exists():
        raise FileNotFoundError(f"Missing: {NODE_SCRIPT}")

    actions: List[Dict[str, Any]] = []
    for js in scan_js_files():
        data = run_node(js)
        if not data:
            continue
        for a in data.get("actions", []):
            a["file"] = str(js.relative_to(PROJECT_ROOT)).replace("\\", "/")
            actions.append(a)

    AUTOGEN.mkdir(parents=True, exist_ok=True)
    ACTION_JSON.write_text(json.dumps({"actions": actions}, ensure_ascii=False, indent=2), encoding="utf-8")
    ACTION_MD.write_text(to_markdown(actions), encoding="utf-8")

    print(f"[OK] {ACTION_JSON}")
    print(f"[OK] {ACTION_MD}")


if __name__ == "__main__":
    main()
