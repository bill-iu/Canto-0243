"""ponytail: assert length+finals uses idx_length_finals after finalize (fails if policy regresses)."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ingest.lexicon_indexes import finalize_lexicon_indexes

DB = REPO / "lyrics.db"


def main() -> int:
    if not DB.is_file():
        print("skip: no lyrics.db", file=sys.stderr)
        return 0
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
        copy = Path(fh.name)
    try:
        copy.write_bytes(DB.read_bytes())
        finalize_lexicon_indexes(copy)
        con = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
        length, finals = con.execute(
            "SELECT length, finals FROM words "
            "WHERE length=2 AND finals IS NOT NULL AND finals != '' LIMIT 1"
        ).fetchone()
        plan = " ".join(
            str(c)
            for row in con.execute(
                "EXPLAIN QUERY PLAN SELECT id FROM words WHERE length=? AND finals=? LIMIT 40",
                (length, finals),
            )
            for c in row
        )
        con.close()
        assert "idx_length_finals" in plan, plan
        print("lexicon-index-audit-self-check ok:", plan)
        return 0
    finally:
        try:
            copy.unlink(missing_ok=True)
        except PermissionError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
