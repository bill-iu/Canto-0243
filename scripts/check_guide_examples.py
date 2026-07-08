#!/usr/bin/env python3
"""
Smoke-check: every guide example query returns at least 1 result.

Reads `frontend/guide-i18n.mjs` manifest (`query` + `mode`).
Warms probe readiness (`warm_guide_probe_readiness`) then runs `search_words`.
教學探針全量閘（Portable）；預設 repo `lyrics.db`，`DATABASE_URL` 可覆寫。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_project_root()))

# Make console output robust on Windows for CJK + special chars
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# This is a docs smoke-check; bypass readiness gate.
os.environ.setdefault("READINESS_GATE_ENFORCE", "0")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal  # noqa: E402
from app.services.query_dispatch import search_words  # noqa: E402
from scripts.guide_manifest import load_manifest_examples  # noqa: E402
from scripts.guide_probe_readiness import warm_guide_probe_readiness  # noqa: E402


def main() -> int:
    examples = load_manifest_examples()
    if not examples:
        print("No guide examples found in manifest.")
        return 2

    failures: list[tuple[str, str]] = []
    db = SessionLocal()
    try:
        warm_guide_probe_readiness(db)
        for q, mode in examples:
            try:
                items = search_words(q=q, code=None, char=None, mode=mode, limit=1, offset=0, db=db)
            except Exception as e:
                failures.append((f"{q} (EXCEPTION: {type(e).__name__}: {e})", mode))
                continue
            if not items:
                failures.append((q, mode))
    finally:
        db.close()

    if failures:
        print("Guide examples with 0 results (or error):")
        for q, mode in failures:
            print(f"  - q={q!r} mode={mode}")
        print(f"\nFAIL ({len(failures)}/{len(examples)})")
        return 1

    print(f"OK ({len(examples)} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())