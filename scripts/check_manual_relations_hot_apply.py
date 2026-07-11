"""ponytail: 關係補錄熱套用 self-check — clear + apply + pool probe."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, ensure_word_relations_table
from app.domain.relations.pool_projection import project_relation_pool
from app.models.word import WordRelation
from ingest.manual_relations_apply import hot_apply_manual_relations


def main() -> int:
    ensure_word_relations_table()
    tsv = ROOT / "data" / "relations" / "manual_relations.tsv"
    if not tsv.is_file() or tsv.stat().st_size < 40:
        print("manual_relations self-check: skip (empty TSV)")
        return 0

    with SessionLocal() as db:
        before = (
            db.query(WordRelation)
            .filter(WordRelation.source == "manual")
            .count()
        )
        stats = hot_apply_manual_relations(db, tsv)
        after = (
            db.query(WordRelation)
            .filter(WordRelation.source == "manual")
            .count()
        )
        if stats["applied"] + stats["skipped_exists"] < 1:
            raise SystemExit(f"hot-apply applied nothing: {stats}")
        if after < 1:
            raise SystemExit(f"expected manual rows after apply, got {after} ({stats})")

        pool = project_relation_pool(db, "健壯", allow_inject=False)
        if not pool.ants and not pool.syns:
            raise SystemExit("健壯 pool empty after manual apply")

    print(
        f"manual_relations self-check ok: before={before} after={after} stats={stats}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
