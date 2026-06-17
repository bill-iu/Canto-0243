#!/usr/bin/env python3
"""
Smoke-check: every guide example query returns at least 1 result.

Reads frontend/index.html buttons: `data-query` + `data-mode`.
Runs `search_words` against local `lyrics.db` (DATABASE_URL fallback applies).
"""

from __future__ import annotations

import os
import re
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


DATA_ATTR_RE = re.compile(r'data-query="([^"]+)"\s+data-mode="([^"]+)"')


def extract_examples(html: str) -> list[tuple[str, str]]:
    examples: list[tuple[str, str]] = []
    for q, mode in DATA_ATTR_RE.findall(html):
        examples.append((q, mode))
    return examples


def main() -> int:
    html_path = _project_root() / "frontend" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    examples = extract_examples(html)
    if not examples:
        print("No guide examples found.")
        return 2

    failures: list[tuple[str, str]] = []
    db = SessionLocal()
    try:
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

