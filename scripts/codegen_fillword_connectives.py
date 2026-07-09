#!/usr/bin/env python3
"""Codegen FILLWORD connectives from contracts/fillword-connectives.json (P1 #1).

Writes:
  app/services/_generated/fillword_connectives.py
  client/src/db/_generated/fillword-connectives.ts
  inlines const into client/src/db/query/mode-detect.ts (no import; mjs codegen stays pure)

Usage:
  python scripts/codegen_fillword_connectives.py
  python scripts/codegen_fillword_connectives.py --check
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts" / "fillword-connectives.json"
PY_OUT = REPO / "app" / "services" / "_generated" / "fillword_connectives.py"
TS_OUT = REPO / "client" / "src" / "db" / "_generated" / "fillword-connectives.ts"
MODE_DETECT = REPO / "client" / "src" / "db" / "query" / "mode-detect.ts"
MODE_DETECT_CODEGEN = REPO / "scripts" / "codegen_query_mode_detect.py"

FILLWORD_LINE_RE = re.compile(
    r"^const FILLWORD_CONNECTIVES = '[^']*';\s*$",
    re.MULTILINE,
)


def load_connectives() -> str:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    raw = data.get("connectives")
    if not isinstance(raw, str) or not raw.strip():
        raise SystemExit("fillword-connectives.json: connectives must be non-empty string")
    if len(set(raw)) != len(raw):
        raise SystemExit("fillword-connectives.json: connectives must be unique chars")
    return raw


def render_py(connectives: str) -> str:
    return (
        '"""AUTO-GENERATED from contracts/fillword-connectives.json — do not edit.\n\n'
        "Run: python scripts/codegen_fillword_connectives.py\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        f'FILLWORD_CONNECTIVES_STR = "{connectives}"\n'
        "FILLWORD_CONNECTIVES = frozenset(FILLWORD_CONNECTIVES_STR)\n"
    )


def render_ts(connectives: str) -> str:
    return (
        "/** AUTO-GENERATED from contracts/fillword-connectives.json — do not edit.\n"
        " * Run: python scripts/codegen_fillword_connectives.py\n"
        " */\n\n"
        f"export const FILLWORD_CONNECTIVES = '{connectives}';\n\n"
        "export const FILLWORD_CONNECTIVES_SET: ReadonlySet<string> = new Set(\n"
        "  FILLWORD_CONNECTIVES.split(''),\n"
        ");\n"
    )


def render_mode_detect_line(connectives: str) -> str:
    return f"const FILLWORD_CONNECTIVES = '{connectives}';"


def apply_mode_detect(src: str, connectives: str) -> str:
    line = render_mode_detect_line(connectives)
    if not FILLWORD_LINE_RE.search(src):
        raise SystemExit("mode-detect.ts: missing const FILLWORD_CONNECTIVES = '…';")
    return FILLWORD_LINE_RE.sub(line, src, count=1)


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if generated files would change",
    )
    parser.add_argument(
        "--skip-mjs",
        action="store_true",
        help="Do not run codegen_query_mode_detect after write",
    )
    args = parser.parse_args(argv)
    connectives = load_connectives()
    py = render_py(connectives)
    ts = render_ts(connectives)
    mode_src = MODE_DETECT.read_text(encoding="utf-8")
    mode_out = apply_mode_detect(mode_src, connectives)

    if args.check:
        ok = True
        for path, content in ((PY_OUT, py), (TS_OUT, ts), (MODE_DETECT, mode_out)):
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"stale: {path.relative_to(REPO)}", file=sys.stderr)
                ok = False
        if not ok:
            print("run: python scripts/codegen_fillword_connectives.py", file=sys.stderr)
            return 1
        print("fillword-connectives codegen clean")
        return 0

    changed: list[Path] = []
    if write_if_changed(PY_OUT, py):
        changed.append(PY_OUT)
    if write_if_changed(TS_OUT, ts):
        changed.append(TS_OUT)
    if write_if_changed(MODE_DETECT, mode_out):
        changed.append(MODE_DETECT)
    for path in changed:
        print(f"wrote {path.relative_to(REPO)}")
    if not changed:
        print("fillword-connectives already up to date")

    if not args.skip_mjs:
        proc = subprocess.run(
            [sys.executable, str(MODE_DETECT_CODEGEN)],
            cwd=REPO,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
