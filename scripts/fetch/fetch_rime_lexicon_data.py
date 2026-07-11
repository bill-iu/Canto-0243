#!/usr/bin/env python3
"""Download the approved rime-cantonese-upstream lexical CSV categories."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch._download import download_file

OUT_DIR = REPO_ROOT / "data" / "lexicon" / "raw" / "rime-cantonese-upstream"
BASE_URL = "https://raw.githubusercontent.com/CanCLID/rime-cantonese-upstream/main"
FILES = (
    "word.csv",
    "fixed_expressions.csv",
    "phrase_fragment.csv",
    "onomatopoeia.csv",
    "trending.csv",
)


def fetch_rime_lexicon_csvs(dest: Path = OUT_DIR) -> list[Path]:
    """Fetch lexical categories only; proper_nouns.csv is deliberately absent."""
    return [download_file(f"{BASE_URL}/{name}", dest / name) for name in FILES]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch categorized Rime Cantonese lexicon data without proper nouns"
    )
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    fetch_rime_lexicon_csvs(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
