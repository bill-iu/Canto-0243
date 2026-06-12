#!/usr/bin/env python3
"""Smoke-bench README critical search cases (latency + top-N dump). Requires local lyrics.db."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Make console output robust on Windows for CJK + special chars
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal
from app.services.word_search_service import search_words
from app.services.word_serializer import get_word_jyutping, get_word_sort_code, get_word_text

db = SessionLocal()
try:
    critical_cases = [
        ("事業", "m1"),
        ("事業", "m2"),
        ("門0", "m1"),
        ("門0", "m2"),
        ("好23", "m1"),
        ("好23", "m2"),
        ("_識_", "m1"),
        ("快樂", "syn"),
        ("香港=", "m1"),
        ("香=?", "m1"),
        ("23就", "m1"),
        ("23@就", "m1"),
        ("2=我3", "m1"),
        ("2我=3", "m1"),
    ]
    for q, mode in critical_cases:
        t0 = time.perf_counter()
        results = search_words(q=q, code=None, char=None, mode=mode, limit=8, offset=0, db=db)
        dt_ms = (time.perf_counter() - t0) * 1000
        print(f"=== {q} mode={mode} : {dt_ms:.1f} ms ===")
        for i, w in enumerate(results[:5]):
            if isinstance(w, dict):
                print(f"  [{i}] {w}")
            else:
                c = get_word_text(w)
                j = get_word_jyutping(w)
                cd = get_word_sort_code(w)
                print(f"  [{i}] {c} | {j} | code={cd}")
        if q == "門0":
            print("  [門0 codes check] top codes 2nd digit should be 0:")
            for i, w in enumerate(results[:4]):
                if not isinstance(w, dict):
                    cd = get_word_sort_code(w)
                    second = cd[1] if len(cd) > 1 else "?"
                    print(f"    pos{i}: code={cd} (2nd={second}) char={get_word_text(w)}")
        print()
finally:
    db.close()
    print("BENCH_DONE")
