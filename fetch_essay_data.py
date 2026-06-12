#!/usr/bin/env python3
"""
Download rime essay-cantonese corpus for search ranking (P3).

Source: https://github.com/rime/rime-cantonese (essay-cantonese.txt)
Format: 詞<TAB>頻次 — sort signal only, no injection gate.

Usage:
  python fetch_essay_data.py
  python fetch_essay_data.py --verify
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "essay"
ESSAY_URL = (
    "https://raw.githubusercontent.com/rime/rime-cantonese/refs/heads/main/essay-cantonese.txt"
)
OUT_PATH = OUT_DIR / "essay-cantonese.txt"


def fetch_essay_corpus(dest: Path = OUT_PATH) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {ESSAY_URL} ...")
    urllib.request.urlretrieve(ESSAY_URL, dest)
    size = dest.stat().st_size
    print(f"Wrote {dest} ({size:,} bytes)")
    return dest


def verify_sample(path: Path = OUT_PATH) -> None:
    from app.lexicon.essay_index import get_essay_frequency, load_essay_corpus, reset_essay_for_tests

    reset_essay_for_tests()
    count = load_essay_corpus(path)
    print(f"Loaded {count} essay frequency rows")
    for w in ("香港", "開心", "門前"):
        print(f"  {w}: {get_essay_frequency(w)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch essay-cantonese frequency corpus")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    if not args.verify or not args.output.is_file():
        fetch_essay_corpus(args.output)
    if args.verify:
        verify_sample(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
