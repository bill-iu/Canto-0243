"""ponytail: orphan manual-direct merge self-check — merge then no-op."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, ensure_word_relations_table
from app.services.manual_relation_service import create_creator_manual_relation
from ingest.manual_relations_apply import merge_orphan_manual_directs_into_tsv


def main() -> int:
    ensure_word_relations_table()
    with tempfile.TemporaryDirectory() as tmp:
        tsv = Path(tmp) / "manual_relations.tsv"
        tsv.write_text(
            "seed_char\topposite_char\trelation_type\tnote\n"
            "年輕\t年老\tant\t\n",
            encoding="utf-8",
        )
        with SessionLocal() as db:
            # Ensure a direct that is already in TSV + one orphan (if both lexemes exist).
            try:
                create_creator_manual_relation(
                    db,
                    seed_char="肥",
                    opposite_char="瘦",
                    relation_type="ant",
                    expand=False,
                )
                db.commit()
            except Exception:
                db.rollback()

            first = merge_orphan_manual_directs_into_tsv(db, tsv)
            second = merge_orphan_manual_directs_into_tsv(db, tsv)
            if second["merged"] != 0:
                raise SystemExit(f"second merge should be no-op: {second}")
            text = tsv.read_text(encoding="utf-8")
            if "年輕\t年老\tant" not in text:
                raise SystemExit("preserved existing TSV row missing")
            print(f"orphan_manual_merge self-check ok: first={first} second={second}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
