#!/usr/bin/env python3
"""Benchmark ~~ / ~~港 近義複合查詢（暖機後，開發手動跑，不納入 CI）。

用法：
  python scripts/bench_compound_syn.py
  python scripts/bench_compound_syn.py --rounds 20
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
from app.domain.relations.compound_syn import reset_compound_syn_snapshot_for_tests
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.startup.offline_preload import preload_compound_syn_runtime_cache
from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests

DEFAULT_QUERIES = ("~~", "~~港")
P95_BUDGET_MS = 300.0


def _load_rows(db) -> list:
    return (
        db.query(
            Word.char,
            Word.code,
            Word.jyutping,
            Word.finals,
            Word.initials,
            Word.length,
        )
        .all()
    )


def _p95_ms(timings: list[float]) -> float:
    ordered = sorted(timings)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx] * 1000.0


def _bench(queries: tuple[str, ...], rounds: int) -> dict[str, float]:
    reset_word_cache_for_tests()
    reset_compound_syn_snapshot_for_tests()
    db = SessionLocal()
    p95_by_query: dict[str, float] = {}
    try:
        rows = _load_rows(db)
        populate_word_cache_from_rows(rows)
        complete_preload()
        preload_compound_syn_runtime_cache()
        for q in queries:
            timings: list[float] = []
            for _ in range(rounds):
                t0 = time.perf_counter()
                search_words(q=q, mode="m1", db=db, limit=50, offset=0)
                timings.append(time.perf_counter() - t0)
            p95 = _p95_ms(timings)
            p95_by_query[q] = p95
            print(
                f"{q!r:8}  n={len(timings):2}  "
                f"p50={statistics.median(timings)*1000:6.1f}ms  "
                f"p95={p95:6.1f}ms  "
                f"max={max(timings)*1000:6.1f}ms"
            )
    finally:
        db.close()
        reset_compound_syn_snapshot_for_tests()
        reset_word_cache_for_tests()
    return p95_by_query


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark compound-syn (~~) search")
    parser.add_argument("--queries", nargs="*", default=list(DEFAULT_QUERIES))
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--budget-ms", type=float, default=P95_BUDGET_MS)
    parser.add_argument("--enforce", action="store_true", help="Exit 1 if any p95 exceeds budget")
    args = parser.parse_args()
    print("warm compound-syn benchmark (word_cache + snapshot + tier cache)")
    p95_by_query = _bench(tuple(args.queries), max(1, args.rounds))
    if args.enforce:
        over = {q: ms for q, ms in p95_by_query.items() if ms > args.budget_ms}
        if over:
            print(f"FAIL p95 budget {args.budget_ms}ms exceeded: {over}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
