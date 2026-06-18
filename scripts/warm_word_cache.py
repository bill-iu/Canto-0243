#!/usr/bin/env python3
"""預暖詞庫快取索引磁碟快照（Portable build 與維護者 CLI）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.word import Word
from app.utils.word_cache import (
    begin_preload,
    complete_preload,
    persist_word_cache_to_disk,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
)
from app.utils.word_cache_disk import disk_cache_path


def warm_word_cache(*, root: Path | str) -> Path:
    """自 root/lyrics.db 建索引並寫入 root/.cache/word_meta.bin。"""
    bundle = Path(root).resolve()
    db_path = bundle / "lyrics.db"
    if not db_path.is_file():
        raise FileNotFoundError(f"lyrics.db not found under {bundle}")

    reset_word_cache_for_tests()
    begin_preload()

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        rows = (
            session.query(
                Word.char,
                Word.code,
                Word.jyutping,
                Word.finals,
                Word.initials,
                Word.length,
            )
            .filter(Word.length <= 10)
            .all()
        )
    finally:
        session.close()
        engine.dispose()

    populate_word_cache_from_rows(rows)
    complete_preload()
    cache_dir = bundle / ".cache"
    persist_word_cache_to_disk(db_path=db_path, cache_dir=cache_dir)
    out = disk_cache_path(cache_dir=cache_dir)
    if not out.is_file():
        raise RuntimeError(f"failed to write {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Warm word_meta.bin for a portable bundle root.")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Directory containing lyrics.db (default: current directory)",
    )
    args = parser.parse_args(argv)
    try:
        out = warm_word_cache(root=args.root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
