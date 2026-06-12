#!/usr/bin/env python3
"""
Download rime-cantonese-upstream char.csv for single-char lexicon (P2).

Source: https://github.com/CanCLID/rime-cantonese-upstream (CC BY 4.0)

Usage:
  python fetch_rime_data.py
  python fetch_rime_data.py --verify
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "rime"
CHAR_CSV_URL = (
    "https://raw.githubusercontent.com/CanCLID/rime-cantonese-upstream/main/char.csv"
)
OUT_PATH = OUT_DIR / "char.csv"


def fetch_char_csv(dest: Path = OUT_PATH) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {CHAR_CSV_URL} ...")
    urllib.request.urlretrieve(CHAR_CSV_URL, dest)
    size = dest.stat().st_size
    print(f"Wrote {dest} ({size:,} bytes)")
    return dest


def verify_sample(path: Path = OUT_PATH) -> None:
    from app.lexicon.rime_char_index import get_rime_char_entries, load_rime_char_csv, reset_rime_char_for_tests

    reset_rime_char_for_tests()
    count = load_rime_char_csv(path)
    print(f"Loaded {count} pron_rank=預設 single-char entries")
    for ch in ("你", "好", "就"):
        entries = get_rime_char_entries(ch)
        if entries:
            e = entries[0]
            print(f"  {ch}: {e.jyutping} code={e.code}")
        else:
            print(f"  {ch}: (missing)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch rime-cantonese-upstream char.csv")
    parser.add_argument("--verify", action="store_true", help="Load and print sample entries")
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    if not args.verify or not args.output.is_file():
        fetch_char_csv(args.output)
    if args.verify:
        verify_sample(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
