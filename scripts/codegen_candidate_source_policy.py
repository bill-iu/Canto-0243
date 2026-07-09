#!/usr/bin/env python3
"""Codegen candidate source policy from contracts/candidate-source-policy.json (P3 #7).

Writes:
  app/services/_generated/candidate_source_policy.py
  client/src/db/_generated/candidate-source-policy.ts

Usage:
  python scripts/codegen_candidate_source_policy.py
  python scripts/codegen_candidate_source_policy.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts" / "candidate-source-policy.json"
PY_OUT = REPO / "app" / "services" / "_generated" / "candidate_source_policy.py"
TS_OUT = REPO / "client" / "src" / "db" / "_generated" / "candidate-source-policy.ts"


def load_policy() -> dict:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    limit = data.get("candidateFallbackLimit")
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("candidateFallbackLimit must be a positive int")
    return data


def render_py(limit: int) -> str:
    return (
        '"""AUTO-GENERATED from contracts/candidate-source-policy.json — do not edit.\n\n'
        "Run: python scripts/codegen_candidate_source_policy.py\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        f"CANDIDATE_FALLBACK_LIMIT = {limit}\n"
    )


def render_ts(limit: int) -> str:
    return (
        "/** AUTO-GENERATED from contracts/candidate-source-policy.json — do not edit.\n"
        " * Run: python scripts/codegen_candidate_source_policy.py\n"
        " */\n\n"
        f"export const CANDIDATE_FALLBACK_LIMIT = {limit};\n"
    )


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    data = load_policy()
    limit = int(data["candidateFallbackLimit"])
    py = render_py(limit)
    ts = render_ts(limit)

    if args.check:
        ok = True
        for path, content in ((PY_OUT, py), (TS_OUT, ts)):
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"stale: {path.relative_to(REPO)}", file=sys.stderr)
                ok = False
        if not ok:
            print("run: python scripts/codegen_candidate_source_policy.py", file=sys.stderr)
            return 1
        print("candidate-source-policy codegen clean")
        return 0

    changed = []
    if write_if_changed(PY_OUT, py):
        changed.append(PY_OUT)
    if write_if_changed(TS_OUT, ts):
        changed.append(TS_OUT)
    for path in changed:
        print(f"wrote {path.relative_to(REPO)}")
    if not changed:
        print("candidate-source-policy already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
