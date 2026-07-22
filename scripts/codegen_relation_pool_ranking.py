#!/usr/bin/env python3
"""Codegen relation-pool ranking SSOT from contracts/relation-pool-ranking.json.

Writes:
  app/domain/relation_pool/_generated/relation_pool_ranking.py
  client/src/db/relation-pool/_generated/relation-pool-ranking.ts

Usage:
  python scripts/codegen_relation_pool_ranking.py
  python scripts/codegen_relation_pool_ranking.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts" / "relation-pool-ranking.json"
PY_OUT = (
    REPO / "app" / "domain" / "relation_pool" / "_generated" / "relation_pool_ranking.py"
)
TS_OUT = (
    REPO
    / "client"
    / "src"
    / "db"
    / "relation-pool"
    / "_generated"
    / "relation-pool-ranking.ts"
)

def load_contract() -> dict:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    ranks = data.get("source_base_rank")
    sources = data.get("runtime_derived_ant_sources")
    if not isinstance(ranks, dict) or not ranks:
        raise SystemExit("source_base_rank must be a non-empty object")
    for key, value in ranks.items():
        if not isinstance(key, str) or not isinstance(value, int):
            raise SystemExit(f"source_base_rank[{key!r}] must be int")
    if not isinstance(sources, list) or not sources or not all(
        isinstance(s, str) and s for s in sources
    ):
        raise SystemExit("runtime_derived_ant_sources must be a non-empty string list")
    return data


def render_py(data: dict) -> str:
    ranks = data["source_base_rank"]
    sources = data["runtime_derived_ant_sources"]
    rank_lines = ",\n".join(f'    "{k}": {v}' for k, v in ranks.items())
    src_lines = ",\n".join(f'    "{s}"' for s in sources)
    return (
        '"""AUTO-GENERATED from contracts/relation-pool-ranking.json — do not edit.\n'
        "Regenerate: python scripts/codegen_relation_pool_ranking.py\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from typing import Dict\n\n"
        f"SOURCE_BASE_RANK: Dict[str, int] = {{\n{rank_lines},\n}}\n\n"
        "RUNTIME_DERIVED_ANT_SOURCES = frozenset({\n"
        f"{src_lines},\n"
        "})\n"
    )


def render_ts(data: dict) -> str:
    ranks = data["source_base_rank"]
    sources = data["runtime_derived_ant_sources"]
    rank_lines = ",\n".join(f"  '{k}': {v}" for k, v in ranks.items())
    src_lines = ",\n".join(f"  '{s}'" for s in sources)
    return (
        "/** AUTO-GENERATED from contracts/relation-pool-ranking.json — do not edit.\n"
        " * Regenerate: python scripts/codegen_relation_pool_ranking.py\n"
        " */\n"
        "export const SOURCE_BASE_RANK: Record<string, number> = {\n"
        f"{rank_lines},\n"
        "};\n\n"
        "export const RUNTIME_DERIVED_ANT_SOURCES = new Set<string>([\n"
        f"{src_lines},\n"
        "]);\n"
    )


def write_or_check(path: Path, body: str, check: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if check:
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return False
        current = path.read_text(encoding="utf-8")
        if current != body:
            print(f"stale {path}", file=sys.stderr)
            return False
        return True
    path.write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = load_contract()
    ok = write_or_check(PY_OUT, render_py(data), args.check)
    ok = write_or_check(TS_OUT, render_ts(data), args.check) and ok
    if args.check and ok:
        print("relation-pool-ranking codegen ok")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
