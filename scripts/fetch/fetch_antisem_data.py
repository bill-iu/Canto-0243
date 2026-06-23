#!/usr/bin/env python3
"""
Download antisem antonym pairs for runtime static thesaurus + ingest.

Upstream: https://github.com/liuhuanyong/ChineseAntiword (antisem.txt)
No explicit license on upstream — fetch for local use only; see THIRD_PARTY_NOTICES.md.

Usage:
  python scripts/fetch/fetch_antisem_data.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch._download import download_file


def _convert_file_to_traditional(path: Path) -> None:
    try:
        from app.utils.trad_chinese import to_traditional
    except ImportError:
        return
    text = path.read_text(encoding="utf-8")
    path.write_text(to_traditional(text), encoding="utf-8")

ANTISEM_URL = (
    "https://raw.githubusercontent.com/liuhuanyong/ChineseAntiword/master/antisem.txt"
)
OUT_PATH = REPO_ROOT / "data" / "antonym" / "antisem.txt"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch ChineseAntiword antisem.txt")
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    print(
        "Notice: upstream ChineseAntiword has no explicit OSS license. "
        "Use locally; do not redistribute as your own dataset. "
        "See THIRD_PARTY_NOTICES.md."
    )
    download_file(ANTISEM_URL, args.output, label="antisem.txt")
    _convert_file_to_traditional(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
