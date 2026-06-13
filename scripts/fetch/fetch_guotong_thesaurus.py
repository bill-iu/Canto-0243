#!/usr/bin/env python3
"""
Download guotong synonym/antonym dict files for static thesaurus + ingest.

Upstream: https://github.com/guotong1988/chinese_dictionary (Anti-996 License)

Usage:
  python scripts/fetch/fetch_guotong_thesaurus.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch._download import download_file

BASE = "https://raw.githubusercontent.com/guotong1988/chinese_dictionary/master"
OUT_DIR = REPO_ROOT / "data" / "thesaurus"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch guotong thesaurus dict files")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    download_file(f"{BASE}/dict_synonym.txt", args.output_dir / "dict_synonym.txt")
    download_file(f"{BASE}/dict_antonym.txt", args.output_dir / "dict_antonym.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
