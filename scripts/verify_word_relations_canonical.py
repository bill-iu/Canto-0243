#!/usr/bin/env python3
"""Verify word_relations canonical storage (debug session c269d0)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.database import SessionLocal, ensure_word_relations_canonical_unique
from app.models.word import WordRelation
from ingest.relation_canonical import _debug_log


def main() -> int:
    ensure_word_relations_canonical_unique()
    with SessionLocal() as db:
        total = db.query(WordRelation).count()
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
        triple_dupes = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT word_id, related_id, relation_type, COUNT(*) c
                FROM word_relations
                GROUP BY word_id, related_id, relation_type
                HAVING c > 1
            )
        """)).scalar()

    data = {
        "total": total,
        "non_canonical_rows": non_canonical,
        "bidirectional_pairs": bidirectional,
        "triple_duplicate_groups": triple_dupes,
    }
    _debug_log("A", "scripts/verify_word_relations_canonical.py", "verification", data, run_id="verify")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if non_canonical == 0 and bidirectional == 0 and triple_dupes == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
