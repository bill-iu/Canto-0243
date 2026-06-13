#!/usr/bin/env python3
"""Export words-table rows as 詞級標音 JSON for import_data / static_index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB = REPO_ROOT / "lyrics.db"
DEFAULT_OUT = REPO_ROOT / "dist" / "words-lexicon.json"


def export_words_lexicon(db_path: Path) -> list[dict[str, str]]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.word import Word

    engine = create_engine(f"sqlite:///{db_path.resolve().as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    rows: list[dict[str, str]] = []
    try:
        with Session() as db:
            for word in db.query(Word).order_by(Word.char, Word.code, Word.jyutping).all():
                char = (word.char or "").strip()
                jyutping = (word.jyutping or "").strip()
                code = (word.code or "").strip()
                if not char or not jyutping or not code:
                    continue
                rows.append({"char": char, "jyutping": jyutping, "code": code})
    finally:
        engine.dispose()
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export lyrics.db words table to 詞級標音 JSON ({char,jyutping,code}[])"
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"SQLite path (default: {DEFAULT_DB.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUT),
        help=f"Output JSON path (default: {DEFAULT_OUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=0,
        help="JSON indent (0 = compact)",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = export_words_lexicon(db_path)
    payload = json.dumps(rows, ensure_ascii=False, indent=args.indent or None)
    out_path.write_text(payload + "\n", encoding="utf-8")
    print(f"Exported {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
