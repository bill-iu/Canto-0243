#!/usr/bin/env python3
"""
Record words.hk wordslist provenance and optional raw download.

Upstream: https://words.hk/faiman/analysis/wordslist/
License: Public domain (credit words.hk appreciated).

The wordslist JSON/CSV is published via the words.hk browser UI; there is no
stable raw URL in this repo. This script writes a manifest and prints manual
steps. Converting wordslist → 0243-coded clean JSON remains a maintainer step
(see README § 資料來源).

Usage:
  python scripts/fetch/fetch_words_hk_wordslist.py
  python scripts/fetch/fetch_words_hk_wordslist.py --input /path/to/wordslist.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "data" / "raw" / "words.hk"
MANIFEST = OUT_DIR / "manifest.json"
WORDS_PAGE = "https://words.hk/faiman/analysis/wordslist/"


def write_manifest(*, copied: str | None = None) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": WORDS_PAGE,
        "license": "public-domain",
        "attribution": "words.hk",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_file": copied,
        "notes": (
            "Download JSON or CSV from the words.hk wordslist page in a browser, "
            "then pass --input to this script. Build data/raw/clean/*.json separately."
        ),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return MANIFEST


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="words.hk wordslist manifest / copy")
    parser.add_argument(
        "--input",
        type=Path,
        help="Local wordslist JSON or CSV downloaded from words.hk",
    )
    args = parser.parse_args(argv)

    copied: str | None = None
    if args.input:
        if not args.input.is_file():
            print(f"Input not found: {args.input}", file=sys.stderr)
            return 1
        dest = OUT_DIR / args.input.name
        shutil.copy2(args.input, dest)
        copied = str(dest.relative_to(REPO_ROOT))
        print(f"Copied wordslist → {dest}")

    manifest = write_manifest(copied=copied)
    print(f"Wrote manifest → {manifest}")
    print()
    print("words.hk wordslist (public domain; credit words.hk appreciated):")
    print(f"  {WORDS_PAGE}")
    if not args.input:
        print()
        print("No --input file. Open the page above, download JSON or CSV, then re-run:")
        print("  python scripts/fetch/fetch_words_hk_wordslist.py --input <download>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
