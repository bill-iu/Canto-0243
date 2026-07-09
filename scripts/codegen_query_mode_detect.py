#!/usr/bin/env python3
"""Codegen frontend/query-mode-detect.mjs from client/src/db/query/mode-detect.ts.

Usage:
  python scripts/codegen_query_mode_detect.py
  python scripts/codegen_query_mode_detect.py --check
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TS_SRC = REPO / "client" / "src" / "db" / "query" / "mode-detect.ts"
MJS_OUT = REPO / "frontend" / "query-mode-detect.mjs"

HEADER = """\
/**
 * AUTO-GENERATED from client/src/db/query/mode-detect.ts — do not edit.
 * Run: python scripts/codegen_query_mode_detect.py
 */

"""


def strip_ts_to_mjs(src: str) -> str:
    """Minimal TS→plain ESM for this pure detect module (no imports)."""
    m = re.search(r"(const FILLWORD_CONNECTIVES[\s\S]*)", src)
    if not m:
        raise SystemExit("mode-detect.ts: missing FILLWORD_CONNECTIVES body")
    core = m.group(1)
    core = re.sub(r": string\b", "", core)
    core = re.sub(r": boolean\b", "", core)
    if not core.endswith("\n"):
        core += "\n"
    return HEADER + core


def render() -> str:
    return strip_ts_to_mjs(TS_SRC.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not TS_SRC.is_file():
        print(f"missing {TS_SRC}", file=sys.stderr)
        return 1
    content = render()
    if args.check:
        if not MJS_OUT.is_file() or MJS_OUT.read_text(encoding="utf-8") != content:
            print(f"stale: {MJS_OUT.relative_to(REPO)}", file=sys.stderr)
            print("run: python scripts/codegen_query_mode_detect.py", file=sys.stderr)
            return 1
        print("query-mode-detect codegen clean")
        return 0
    MJS_OUT.parent.mkdir(parents=True, exist_ok=True)
    if MJS_OUT.is_file() and MJS_OUT.read_text(encoding="utf-8") == content:
        print("already up to date")
        return 0
    MJS_OUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {MJS_OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
