#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRICT TECH DOC GENERATOR para MEATZE.

- Sin modelos de IA.
- Sin fantasías.
- Solo hechos extraídos del código (Python, JS, HTML).
- Salida en formato técnico Markdown.

Uso:

    source venv/bin/activate
    python ai_docs/gen_md_docs_strict.py --once   # una pasada
"""

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]


SRC_DIRS = [
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "api",
    PROJECT_ROOT / "panel",
    PROJECT_ROOT / "meatze_site",
    PROJECT_ROOT / "utils",
    PROJECT_ROOT / "templates",
    PROJECT_ROOT / "static",
]

OUT_DIR = PROJECT_ROOT / "docs" / "autogen_strict"
INDEX_PATH = OUT_DIR / ".index.json"
FACTS_JSONL = OUT_DIR / "facts.jsonl"
# ---- helpers índice / hash ----

def load_index() -> Dict[str, str]:
    if not INDEX_PATH.exists():
        return {}
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_index(index: Dict[str, str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def file_hash(content: str) -> str:
    import hashlib
    return hashlib.sha1(content.encode("utf-8")).hexdigest()


def rel_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def out_md_path(src_path: Path) -> Path:
    return OUT_DIR / (rel_path(src_path) + ".md")


# ---- ANALISIS PYTHON ----

def analyze_python(path: Path, code: str) -> Dict[str, Any]:
    """
    Extrae funciones, clases, decoradores, posibles endpoints (strings con /meatze/).
    """
    info: Dict[str, Any] = {
        "file": rel_path(path),
        "type": "python",
        "functions": [],
        "classes": [],
        "endpoints": [],
        "strings": []
    }

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return info

    endpoints_set = set()

    class PyVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            decorators = []
            for d in node.decorator_list:
                if isinstance(d, ast.Name):
                    decorators.append(d.id)
                elif isinstance(d, ast.Attribute):
                    decorators.append(d.attr)
                elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
                    decorators.append(d.func.id)

            params = [a.arg for a in node.args.args]
            info["functions"].append({
                "name": node.name,
                "type": "function",
                "params": params,
                "decorators": decorators,
                "lineno": node.lineno
            })
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            params = [a.arg for a in node.args.args]
            info["functions"].append({
                "name": node.name,
                "type": "async_function",
                "params": params,
                "decorators": [],
                "lineno": node.lineno
            })
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            info["classes"].append({
                "name": node.name,
                "methods": methods,
                "lineno": node.lineno
            })
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant):
            if isinstance(node.value, str):
                s = node.value
                info["strings"].append(s)
                if "/meatze" in s or s.startswith("/"):
                    endpoints_set.add(s)
            self.generic_visit(node)

    PyVisitor().visit(tree)
    info["endpoints"] = sorted(endpoints_set)
    return info


# ---- ANALISIS JS (via Node + esprima) ----

JS_INTROSPECTOR = PROJECT_ROOT / "ai_docs" / "js_introspect_acorn.mjs"

def analyze_js(path: Path, code: str) -> Dict[str, Any]:
    """
    Llama a node js_introspect.mjs y devuelve estructura técnica.
    """
    info: Dict[str, Any] = {
        "file": rel_path(path),
        "type": "js",
        "functions": [],
        "calls": [],
        "domSelectors": [],
        "events": [],
        "globals": [],
        "endpoints": []
    }

    if not JS_INTROSPECTOR.exists():
        return info

    try:
        proc = subprocess.run(
            ["node", str(JS_INTROSPECTOR), str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
    except Exception as e:
        print(f"[JS] Error ejecutando Node: {e}")
        return info

    if proc.returncode != 0:
        print(f"[JS] Introspector error for {path}: {proc.stderr.strip()}")
        return info

    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        print(f"[JS] Error parseando JSON de introspector: {e}")
        return info

    info["functions"] = data.get("functions", []) or []
    info["callsSignificant"] = data.get("callsSignificant", []) or []
    info["domSelectors"] = data.get("domSelectors", []) or []
    info["events"] = data.get("events", []) or []
    info["globals"] = data.get("globals", []) or []
    info["stringLiterals"] = data.get("stringLiterals", []) or []
    info["selectorAliases"] = data.get("selectorAliases", []) or []
    info["apiBases"] = data.get("apiBases", {}) or {}

    info["endpoints"] = data.get("endpoints", []) or []
    info["endpointsTemplates"] = data.get("endpointsTemplates", []) or []
    info["endpointsParts"] = data.get("endpointsParts", []) or []



    return info


# ---- ANALISIS HTML ----

ID_RE = re.compile(r'id="([^"]+)"')
CLASS_RE = re.compile(r'class="([^"]+)"')
FORM_RE = re.compile(r'<form[^>]*>', re.IGNORECASE)

def analyze_html(path: Path, code: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "file": rel_path(path),
        "type": "html",
        "ids": [],
        "classes": [],
        "forms": [],
        "blocks": [],
        "includes": [],
        "vars": []
    }

    info["ids"] = sorted(set(ID_RE.findall(code)))

    classes = set()
    for m in CLASS_RE.findall(code):
        for c in m.split():
            classes.add(c)
    info["classes"] = sorted(classes)

    info["forms"] = FORM_RE.findall(code)

    # шаблонные конструкции Django
    info["blocks"] = re.findall(r'{%\s*block\s+(\w+)\s*%}', code)
    info["includes"] = re.findall(r'{%\s*include\s+"([^"]+)"\s*%}', code)
    info["vars"] = re.findall(r'{{\s*([^}\s]+)\s*}}', code)

    return info


# ---- FORMATEO A MARKDOWN (ТЕХНИЧЕСКИЙ) ----

def py_info_to_md(info: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Archivo: {info['file']}")
    lines.append("")
    lines.append("## Tipo de archivo")
    lines.append("python")
    lines.append("")

    lines.append("## Funciones")
    if not info["functions"]:
        lines.append("- (ninguna detectada)")
    else:
        for fn in info["functions"]:
            lines.append(f"- {fn['name']}:")
            lines.append(f"    - tipo: {fn['type']}")
            lines.append(f"    - línea: {fn['lineno']}")
            lines.append(f"    - argumentos: {', '.join(fn['params']) if fn['params'] else '(sin parámetros)'}")
            if fn.get("decorators"):
                lines.append(f"    - decoradores: {', '.join(fn['decorators'])}")
    lines.append("")

    lines.append("## Clases")
    if not info["classes"]:
        lines.append("- (ninguna detectada)")
    else:
        for cls in info["classes"]:
            lines.append(f"- {cls['name']} (línea {cls['lineno']}): métodos = {', '.join(cls['methods']) or '(ninguno)'}")
    lines.append("")

    lines.append("## Endpoints detectados (strings)")
    if not info["endpoints"]:
        lines.append("- (ninguno detectado)")
    else:
        for ep in info["endpoints"]:
            lines.append(f"- {ep}")
    lines.append("")
    return "\n".join(lines)


def js_info_to_md(info: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Archivo: {info['file']}")
    lines.append("")
    lines.append("## Tipo de archivo")
    lines.append("js")
    lines.append("")

    lines.append("## Funciones")
    if not info["functions"]:
        lines.append("- (ninguna detectada)")
    else:
        for fn in info["functions"]:
            name = fn.get("name") or "(anónima)"
            params = fn.get("params") or []
            loc = fn.get("loc") or {}
            line = loc.get("start", {}).get("line") if isinstance(loc, dict) else None
            lines.append(f"- {name}:")
            lines.append(f"    - tipo: {fn.get('type')}")
            lines.append(f"    - línea: {line if line else '(desconocida)'}")
            lines.append(f"    - argumentos: {', '.join([p for p in params if p]) or '(sin parámetros)'}")
    lines.append("")
    lines.append("## API bases detectadas")
    api_bases = info.get("apiBases") or {}
    if not api_bases:
        lines.append("- (ninguna detectada)")
    else:
        for k in sorted(api_bases.keys()):
            lines.append(f"- {k} = {api_bases[k]}")
    lines.append("")

    lines.append("## Endpoints detectados (literales)")
    eps = info.get("endpoints") or []
    if not eps:
        lines.append("- (ninguno detectado)")
    else:
        for ep in eps:
            lines.append(f"- {ep}")
    lines.append("")

    lines.append("## Endpoints detectados (templates)")
    eps_t = info.get("endpointsTemplates") or []
    if not eps_t:
        lines.append("- (ninguno detectado)")
    else:
        for t in eps_t:
            lines.append(f"- {t}")
    lines.append("")

    lines.append("## Endpoints detectados (partes / strings)")
    eps_p = info.get("endpointsParts") or []
    if not eps_p:
        lines.append("- (ninguno detectado)")
    else:
        for s in eps_p:
            lines.append(f"- {s}")
    lines.append("")


    lines.append("## Selectores DOM usados")
    if not info["domSelectors"]:
        lines.append("- (ninguno detectado)")
    else:
        for s in info["domSelectors"]:
            lines.append(f"- {s}")
    lines.append("")

    lines.append("## Eventos registrados (addEventListener)")
    if not info["events"]:
        lines.append("- (ninguno detectado)")
    else:
        for ev in info["events"]:
            lines.append(f"- {ev}")
    lines.append("")
    lines.append("## Llamadas significativas (fetch/apiJSON/addEventListener/dispatchEvent)")
    cs = info.get("callsSignificant") or []
    if not cs:
        lines.append("- (ninguna detectada)")
    else:
        for c in cs[:200]:
            callee = c.get("callee")
            line = c.get("line")
            arg0 = (c.get("args") or [None])[0]
            lines.append(f"- {callee} @ line {line}: arg0={arg0}")
        if len(cs) > 200:
            lines.append(f"- ... ({len(cs)-200} más)")
    lines.append("")

    lines.append("## Variables globales declaradas")
    if not info["globals"]:
        lines.append("- (ninguna detectada)")
    else:
        for g in info["globals"]:
            lines.append(f"- {g}")
    lines.append("")

    return "\n".join(lines)


def html_info_to_md(info: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Archivo: {info['file']}")
    lines.append("")
    lines.append("## Tipo de archivo")
    lines.append("html")
    lines.append("")

    lines.append("## IDs de elementos")
    if not info["ids"]:
        lines.append("- (ninguno detectado)")
    else:
        for i in info["ids"]:
            lines.append(f"- {i}")
    lines.append("")

    lines.append("## Clases CSS usadas")
    if not info["classes"]:
        lines.append("- (ninguna detectada)")
    else:
        for c in info["classes"]:
            lines.append(f"- {c}")
    lines.append("")

    lines.append("## Formularios detectados (<form>)")
    if not info["forms"]:
        lines.append("- (ninguno detectado)")
    else:
        for f in info["forms"]:
            lines.append(f"- {f}")
    lines.append("")

    lines.append("## Bloques de plantilla ({% block %})")
    if not info["blocks"]:
        lines.append("- (ninguno detectado)")
    else:
        for b in info["blocks"]:
            lines.append(f"- {b}")
    lines.append("")

    lines.append("## Includes de plantilla ({% include %})")
    if not info["includes"]:
        lines.append("- (ninguno detectado)")
    else:
        for inc in info["includes"]:
            lines.append(f"- {inc}")
    lines.append("")

    lines.append("## Variables de plantilla ({{ ... }})")
    if not info["vars"]:
        lines.append("- (ninguna detectada)")
    else:
        for v in info["vars"]:
            lines.append(f"- {v}")
    lines.append("")

    return "\n".join(lines)


# ---- GENERACIÓN POR ARCHIVO ----

def generate_md_for_file(path: Path, index: Dict[str, str]) -> bool:
    if not path.exists() or not path.is_file():
        return False

    suffix = path.suffix.lower()
    if suffix not in {".py", ".js", ".html"}:
        return False

    rel = rel_path(path)
    try:
        code = path.read_text(encoding="utf-8")
    except Exception:
        return False

    h = file_hash(code)
    if index.get(rel) == h:
        return False

    print(f"[DOC] {rel}")

    if suffix == ".py":
        info = analyze_python(path, code)
        md = py_info_to_md(info)
    elif suffix == ".js":
        info = analyze_js(path, code)
        md = js_info_to_md(info)
    else:
        info = analyze_html(path, code)
        md = html_info_to_md(info)

    out_path = out_md_path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    # append facts for RAG (strict)
    fact = {"path": rel, "type": info.get("type")}

    if info.get("type") == "js":
        fact.update({
          "functions": info.get("functions"),
          "apiBases": info.get("apiBases"),
          "endpoints": info.get("endpoints"),
          "endpointsTemplates": info.get("endpointsTemplates"),
          "endpointsParts": info.get("endpointsParts"),
          "domSelectors": info.get("domSelectors"),
          "events": info.get("events"),
          "globals": info.get("globals"),
        })
    elif info.get("type") == "python":
        fact.update({
          "functions": info.get("functions"),
          "classes": info.get("classes"),
          "endpoints": info.get("endpoints"),
        })
    elif info.get("type") == "html":
        fact.update({
          "ids": info.get("ids"),
          "classes": info.get("classes"),
          "forms": info.get("forms"),
          "blocks": info.get("blocks"),
          "includes": info.get("includes"),
          "vars": info.get("vars"),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with FACTS_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fact, ensure_ascii=False) + "\n")


    index[rel] = h
    return True


def iter_source_files():
    for base in SRC_DIRS:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", "migrations", ".git", "node_modules"}]
            for name in files:
                p = Path(root) / name
                if p.suffix.lower() in {".py", ".js", ".html"}:
                    yield p


def process_all_changed_files(index: Dict[str, str]) -> int:
    updated = 0
    for p in iter_source_files():
        if generate_md_for_file(p, index):
            updated += 1
    return updated


# ---- MAIN ----

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Genera documentación una vez.")
    args = parser.parse_args()

    if not args.once:
        args.once = True

    index = load_index()
    # rebuild facts.jsonl each run (strict)
    if FACTS_JSONL.exists():
        FACTS_JSONL.unlink()

    updated = process_all_changed_files(index)
    save_index(index)
    print(f"[INFO] Archivos actualizados: {updated}")


if __name__ == "__main__":
    main()
