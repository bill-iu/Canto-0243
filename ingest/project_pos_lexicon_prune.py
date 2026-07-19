"""Keep only POS SSOT rows whose literal ∈ 詞庫字面集."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence, Set

from ingest.project_pos import (
    DEFAULT_META,
    DEFAULT_TSV,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
)
from ingest.project_pos_cleanup import _rewrite_table

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "lyrics.db"


def load_curated_literals() -> Set[str]:
    """詞級標音 curated 字面（rebuild 前亦算 POS membership 候選）。"""
    path = ROOT / "data" / "lexicon" / "curated_lexicon.json"
    if not path.is_file():
        return set()
    import json

    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {str(r.get("char") or "").strip() for r in rows if r.get("char")}


def load_lexicon_literals(db_path: Path = DEFAULT_DB, *, include_curated: bool = False) -> Set[str]:
    """詞庫字面集。預設 = lyrics.db；POS SSOT 校驗可 include_curated=True（ADR-0060 K4）。"""
    if not db_path.is_file():
        alt = ROOT / "client" / "public" / "lyrics.db"
        db_path = alt if alt.is_file() else db_path
    if not db_path.is_file():
        raise FileNotFoundError(f"missing lyrics.db at {db_path}")
    con = sqlite3.connect(str(db_path))
    try:
        lex = {r[0] for r in con.execute("SELECT DISTINCT char FROM words") if r[0]}
    finally:
        con.close()
    if include_curated:
        lex |= load_curated_literals()
    return lex


def prune(*, db_path: Path = DEFAULT_DB, dry_run: bool = False) -> dict:
    lex = load_lexicon_literals(db_path)
    table = parse_project_pos_tsv()
    before = len(table)
    dropped_types: Counter = Counter()
    for lit, row in table.items():
        if lit in lex:
            continue
        if row.gate_pos():
            dropped_types["gate"] += 1
        elif row.pos <= frozenset({"u"}):
            dropped_types["u"] += 1
        else:
            dropped_types["other"] += 1
    kept = {k: v for k, v in table.items() if k in lex}
    after = len(kept)
    if not dry_run:
        _rewrite_table(kept)
        write_carrier()
        meta = load_meta()
        meta["version"] = "0.4.0"
        meta["lexicon_only"] = {
            "enabled": True,
            "lexicon_literals": len(lex),
            "ssot_before": before,
            "ssot_after": after,
            "dropped": before - after,
            "dropped_types": dict(dropped_types),
        }
        DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "lexicon_literals": len(lex),
        "ssot_before": before,
        "ssot_after": after,
        "dropped": before - after,
        "dropped_types": dict(dropped_types),
        "dry_run": dry_run,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_lexicon_prune")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("dry-run", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("--db", default=str(DEFAULT_DB))
    args = p.parse_args(argv)
    dry = args.cmd == "dry-run"
    print(json.dumps(prune(db_path=Path(args.db), dry_run=dry), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
