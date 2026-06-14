#!/usr/bin/env python3
"""Benchmark 缺字／韻／聲錨代表查詢（開發用，不納入 CI）。

用法：
  python scripts/bench_mask_search.py
  python scripts/bench_mask_search.py --queries "香??" "?就="
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests

DEFAULT_QUERIES = ("??就=", "?就=", "香??", "香=?")


def _load_rows(db, *, max_length: int = 10) -> list:
    return (
        db.query(
            Word.char,
            Word.code,
            Word.jyutping,
            Word.finals,
            Word.initials,
            Word.length,
        )
        .filter(Word.length <= max_length)
        .all()
    )


def _bench(queries: tuple[str, ...], rounds: int) -> None:
    reset_word_cache_for_tests()
    db = SessionLocal()
    try:
        rows = _load_rows(db)
        populate_word_cache_from_rows(rows)
        complete_preload()
        for q in queries:
            timings: list[float] = []
            for _ in range(rounds):
                t0 = time.perf_counter()
                search_words(q=q, mode="m1", db=db, limit=50, offset=0)
                timings.append(time.perf_counter() - t0)
            print(
                f"{q!r:10}  n={len(timings):2}  "
                f"p50={statistics.median(timings)*1000:6.1f}ms  "
                f"p95={sorted(timings)[max(0, int(len(timings)*0.95)-1)]*1000:6.1f}ms  "
                f"max={max(timings)*1000:6.1f}ms"
            )
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark mask / rhyme-anchor search")
    parser.add_argument("--queries", nargs="*", default=list(DEFAULT_QUERIES))
    parser.add_argument("--rounds", type=int, default=12)
    args = parser.parse_args()
    print("cache-ready benchmark (word_cache + indexes loaded)")
    _bench(tuple(args.queries), max(1, args.rounds))


if __name__ == "__main__":
    main()
