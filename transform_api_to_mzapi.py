#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import argparse
from pathlib import Path

# Ищем: await api( URL_EXPR , OPTS_EXPR )
# URL_EXPR берём как "до первой запятой", OPTS_EXPR — до закрывающей скобки.
# Ограничение: рассчитано на простой кейс, где url_expr не содержит запятых.
CALL_RE = re.compile(
    r"""
    (?P<prefix>\bawait\s+)?
    (?P<fn>\bapi)\s*\(\s*
      (?P<url>[^,\n]+?)\s*,\s*
      (?P<opts>[^)\n]+?)\s*
    \)\s*;
    """,
    re.VERBOSE
)

# Вытягиваем из url_expr строковой литерал вида '/auth/request_pin' или "auth/request_pin"
# Берём ПОСЛЕДНИЙ найденный строковой литерал (обычно это и есть хвост эндпоинта).
STR_LIT_RE = re.compile(r"""(['"])(?P<s>.*?)(\1)""")


def derive_action_key(url_expr: str) -> str | None:
    """
    Пытаемся вывести actionKey из последнего строкового литерала в url_expr.
    Пример: V5+'/auth/request_pin' -> '/auth/request_pin' -> 'auth.request_pin'
    """
    lits = [m.group("s") for m in STR_LIT_RE.finditer(url_expr)]
    if not lits:
        return None

    tail = lits[-1].strip()
    if not tail:
        return None

    # хотим именно путь (обычно начинается с '/')
    # если путь без '/', тоже ок, но должен быть "похож" на endpoint
    if "/" not in tail and "\\" not in tail:
        return None

    tail = tail.replace("\\", "/")
    tail = tail.lstrip("/")  # '/auth/request_pin' -> 'auth/request_pin'

    # выкидываем возможные префиксы, если вдруг попадут
    tail = re.sub(r"^(meatze/)?v\d+/", "", tail)

    # делаем actionKey: auth/request_pin -> auth.request_pin
    action = tail.replace("/", ".").strip(".")

    # простая валидация, чтобы не получить мусор
    if not re.match(r"^[a-zA-Z0-9_.\-]+$", action):
        return None

    return action


def transform_text(text: str) -> tuple[str, int]:
    def repl(m: re.Match) -> str:
        url_expr = m.group("url").strip()
        opts_expr = m.group("opts").strip()

        action = derive_action_key(url_expr)
        if not action:
            # не уверены — не трогаем
            return m.group(0)

        # сохраняем наличие await, если было
        await_prefix = m.group("prefix") or ""

        return f"{await_prefix}mzApi('{action}', {url_expr}, {opts_expr});"

    new_text, n = CALL_RE.subn(repl, text)
    return new_text, n


def process_file(path: Path, dry_run: bool) -> int:
    src = path.read_text(encoding="utf-8", errors="replace")
    out, n = transform_text(src)

    if n == 0:
        return 0

    if dry_run:
        print(f"[DRY] {path}: would change {n} call(s)")
        return n

    bak = path.with_suffix(path.suffix + ".bak")
    bak.write_text(src, encoding="utf-8")
    path.write_text(out, encoding="utf-8")
    print(f"[OK] {path}: changed {n} call(s), backup -> {bak.name}")
    return n


def main():
    ap = argparse.ArgumentParser(description="Replace await api(url, opts) -> await mzApi(actionKey, url, opts)")
    ap.add_argument("files", nargs="+", help="Files to transform (html/js/txt)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write, only report")
    args = ap.parse_args()

    total = 0
    for f in args.files:
        p = Path(f)
        if p.is_dir():
            # рекурсивно по директории
            for fp in p.rglob("*.*"):
                if fp.suffix.lower() in {".html", ".js", ".txt"}:
                    total += process_file(fp, args.dry_run)
        else:
            total += process_file(p, args.dry_run)

    print(f"Done. Total changed calls: {total}")


if __name__ == "__main__":
    main()
