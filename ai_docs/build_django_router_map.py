#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "docs" / "autogen_strict"
OUT_JSON = OUT_DIR / "router_map.json"
OUT_MD = OUT_DIR / "router_map.md"

URLCONF_ROOT = "meatze_site.urls"  # поменяй, если у тебя другое


def mod_to_path(mod: str) -> Path:
  return PROJECT_ROOT / (mod.replace(".", "/") + ".py")


def safe_read(p: Path) -> str:
  return p.read_text(encoding="utf-8", errors="replace")


def is_name(node: ast.AST, s: str) -> bool:
  return isinstance(node, ast.Name) and node.id == s


def is_attr(node: ast.AST, attr: str) -> bool:
  return isinstance(node, ast.Attribute) and node.attr == attr


def lit_str(node: ast.AST) -> Optional[str]:
  if isinstance(node, ast.Constant) and isinstance(node.value, str):
    return node.value
  return None


def dotted_name(node: ast.AST) -> Optional[str]:
  # Name or Attribute chain: views.home -> "views.home"
  if isinstance(node, ast.Name):
    return node.id
  if isinstance(node, ast.Attribute):
    left = dotted_name(node.value)
    if left:
      return left + "." + node.attr
  return None


def collect_import_aliases(tree: ast.Module) -> Dict[str, str]:
  # map alias -> module or module.attr
  m: Dict[str, str] = {}
  for n in tree.body:
    if isinstance(n, ast.Import):
      for a in n.names:
        m[a.asname or a.name] = a.name
    elif isinstance(n, ast.ImportFrom):
      mod = n.module or ""
      for a in n.names:
        full = f"{mod}.{a.name}" if mod else a.name
        m[a.asname or a.name] = full
  return m


def resolve_view_ref(view_node: ast.AST, imports: Dict[str, str]) -> str:
  dn = dotted_name(view_node)
  if not dn:
    return "(unresolved)"
  # if first part is an alias in imports, expand it
  parts = dn.split(".")
  head = parts[0]
  if head in imports:
    base = imports[head]
    rest = ".".join(parts[1:])
    return base + (("." + rest) if rest else "")
  return dn


def parse_urlpatterns(module: str, visited: set) -> List[Dict[str, Any]]:
  if module in visited:
    return []
  visited.add(module)

  p = mod_to_path(module)
  if not p.exists():
    return [{"type": "warning", "module": module, "msg": "module file not found"}]

  src = safe_read(p)
  tree = ast.parse(src, filename=str(p))
  imports = collect_import_aliases(tree)

  routes: List[Dict[str, Any]] = []

  # find "urlpatterns = [...]"
  for n in tree.body:
    if isinstance(n, ast.Assign):
      for t in n.targets:
        if isinstance(t, ast.Name) and t.id == "urlpatterns":
          if isinstance(n.value, (ast.List, ast.Tuple)):
            for el in n.value.elts:
              r = parse_urlpattern_item(el, imports, visited)
              if r:
                if isinstance(r, list):
                  routes.extend(r)
                else:
                  routes.append(r)

  return routes


def parse_urlpattern_item(node: ast.AST, imports: Dict[str, str], visited: set) -> Optional[Any]:
  # path("x/", view) / re_path(r"...", view) / include("mod.urls")
  if isinstance(node, ast.Call):
    fn = dotted_name(node.func) or ""
    fn_short = fn.split(".")[-1]

    if fn_short in ("path", "re_path"):
      # args: route, view, kwargs...
      route = lit_str(node.args[0]) if node.args else None
      view = node.args[1] if len(node.args) > 1 else None
      name_kw = None
      for kw in node.keywords or []:
        if kw.arg == "name":
          name_kw = lit_str(kw.value)
      return {
        "type": "route",
        "route": route or "(non-literal)",
        "view": resolve_view_ref(view, imports) if view else "(missing)",
        "name": name_kw,
        "raw": ast.get_source_segment(safe_read(mod_to_path(imports.get(fn.split('.')[0], fn.split('.')[0]) if fn else URLCONF_ROOT)), node) if False else None
      }

    if fn_short == "include":
      # include("app.urls") or include(("app.urls", "ns"), namespace="x")
      inc0 = node.args[0] if node.args else None
      inc_mod = lit_str(inc0)
      if inc_mod:
        return {
          "type": "include",
          "module": inc_mod,
          "routes": parse_urlpatterns(inc_mod, visited)
        }
      return {"type": "include", "module": "(non-literal)", "routes": []}

  return None


def discover_views_files() -> List[Path]:
  # scan common places for view files
  files: List[Path] = []
  for p in PROJECT_ROOT.rglob("views*.py"):
    if "venv" in p.parts:
      continue
    files.append(p)
  return sorted(files)


def extract_render_templates(py_file: Path) -> Dict[str, List[str]]:
  # returns map: function_name -> list of template strings used in render(...)
  src = safe_read(py_file)
  tree = ast.parse(src, filename=str(py_file))

  func_templates: Dict[str, List[str]] = {}

  class FuncVisitor(ast.NodeVisitor):
    def __init__(self):
      self.stack: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
      self.stack.append(node.name)
      self.generic_visit(node)
      self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
      self.stack.append(node.name)
      self.generic_visit(node)
      self.stack.pop()

    def visit_Call(self, node: ast.Call):
      fn = dotted_name(node.func) or ""
      fn_short = fn.split(".")[-1]
      if fn_short == "render" and len(node.args) >= 2:
        tpl = lit_str(node.args[1])
        if tpl and self.stack:
          func_templates.setdefault(self.stack[-1], []).append(tpl)
      self.generic_visit(node)

  v = FuncVisitor()
  v.visit(tree)

  # unique
  for k in list(func_templates.keys()):
    func_templates[k] = sorted(set(func_templates[k]))
  return func_templates


def build_router_map() -> Dict[str, Any]:
  visited = set()
  routes = parse_urlpatterns(URLCONF_ROOT, visited)

  # flatten includes into a single list while keeping include tree
  all_routes: List[Dict[str, Any]] = []

  def flatten(xs: List[Dict[str, Any]], prefix: str = ""):
    for r in xs:
      if r.get("type") == "route":
        all_routes.append({**r, "full_prefix": prefix})
      elif r.get("type") == "include":
        # include itself doesn't have prefix in our simple parser (we don’t parse path("", include(...)) nesting yet)
        # We'll still flatten its inner routes.
        flatten(r.get("routes", []), prefix=prefix)

  flatten(routes)

  # templates from views
  view_templates: Dict[str, Dict[str, List[str]]] = {}
  for vf in discover_views_files():
    m = extract_render_templates(vf)
    if m:
      view_templates[str(vf.relative_to(PROJECT_ROOT)).replace("\\", "/")] = m

  return {
    "urlconf_root": URLCONF_ROOT,
    "routes_tree": routes,
    "routes_flat": all_routes,
    "view_templates": view_templates,
  }


def to_md(data: Dict[str, Any]) -> str:
  lines: List[str] = []
  lines.append("# Django Router Map (strict)\n")
  lines.append(f"- urlconf_root: `{data['urlconf_root']}`\n")

  lines.append("## Routes (flat)\n")
  for r in data["routes_flat"][:400]:
    route = r.get("route")
    view = r.get("view")
    name = r.get("name")
    pref = r.get("full_prefix") or ""
    lines.append(f"- `{pref}{route}` → `{view}`" + (f" (name=`{name}`)" if name else ""))

  if len(data["routes_flat"]) > 400:
    lines.append(f"\n- ... ({len(data['routes_flat'])-400} más)\n")

  lines.append("\n## Templates used in views (render)\n")
  vt = data.get("view_templates", {})
  if not vt:
    lines.append("- (none found)\n")
  else:
    for f in sorted(vt.keys()):
      lines.append(f"### {f}")
      for fn, tpls in sorted(vt[f].items()):
        lines.append(f"- `{fn}()`")
        for t in tpls:
          lines.append(f"  - `{t}`")
      lines.append("")
  return "\n".join(lines)


def main():
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  data = build_router_map()
  OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
  OUT_MD.write_text(to_md(data), encoding="utf-8")
  print(f"[OK] {OUT_JSON}")
  print(f"[OK] {OUT_MD}")


if __name__ == "__main__":
  main()
