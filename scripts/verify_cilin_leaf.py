#!/usr/bin/env python3
"""Verify Cilin leaf export/ingest invariants."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal, ensure_word_relations_canonical_unique
from app.models.word import WordRelation
from ingest.cilin_leaf import is_cilin_leaf_code, parse_leaf_group_line

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CILIN = ROOT / "data" / "cilin" / "new_cilin.txt"
SAMPLE_CODES = ("Aa01A01=", "Ab02B01=", "Ca01B01=", "Dd17A02=", "De01B02=", "Dn03A04=")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CILIN
    if not path.exists():
        print(json.dumps({"error": f"file not found: {path}"}, ensure_ascii=False))
        return 1

    lines = path.read_text(encoding="utf-8").splitlines()
    leaf_lines = [ln for ln in lines if parse_leaf_group_line(ln)]
    non_leaf = [ln.split()[0] for ln in lines if ln.strip() and not parse_leaf_group_line(ln)]

    codes_in_file = {ln.split()[0] for ln in leaf_lines}
    missing_samples = [c for c in SAMPLE_CODES if c not in codes_in_file] if path == DEFAULT_CILIN else []

    trad_ok = True
    if "Ca01B01=" in codes_in_file:
        ca01 = next((ln for ln in leaf_lines if ln.startswith("Ca01B01=")), "")
        trad_ok = all(w in ca01 for w in ("陰曆", "舊曆", "農曆")) and "农历" not in ca01

    ensure_word_relations_canonical_unique()
    with SessionLocal() as db:
        total = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
        non_canonical = db.execute(
            text("SELECT COUNT(*) FROM word_relations WHERE word_id > related_id")
        ).scalar()
        bidirectional = db.execute(text("""
            SELECT COUNT(*) FROM word_relations w1
            JOIN word_relations w2
              ON w1.word_id = w2.related_id AND w1.related_id = w2.word_id
             AND w1.relation_type = w2.relation_type
             AND w1.word_id < w2.word_id
        """)).scalar()

    report = {
        "path": str(path),
        "total_lines": len(lines),
        "leaf_lines": len(leaf_lines),
        "non_leaf_line_codes": non_leaf[:10],
        "all_leaf_codes_valid": all(is_cilin_leaf_code(ln.split()[0]) for ln in leaf_lines),
        "missing_sample_codes": missing_samples,
        "ca01b01_traditional_ok": trad_ok,
        "db_syn_relations": total,
        "non_canonical_rows": non_canonical,
        "bidirectional_pairs": bidirectional,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = (
        report["all_leaf_codes_valid"]
        and not missing_samples
        and trad_ok
        and non_canonical == 0
        and bidirectional == 0
    )
    if path != DEFAULT_CILIN:
        ok = report["all_leaf_codes_valid"] and non_canonical == 0 and bidirectional == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
