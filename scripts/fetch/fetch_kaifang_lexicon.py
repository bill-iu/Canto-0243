#!/usr/bin/env python3
"""
Copy 開放詞典 · 粵語詞典 export into lexicon SSOT raw path.

Upstream: https://kaifangcidian.com/xiazai/ (CC BY 3.0)
File must be maintainer-converted to lexicon JSON [{char,jyutping,code}, ...].

Usage:
  python scripts/fetch/fetch_kaifang_lexicon.py --input /path/to/cantonese.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "lexicon" / "raw" / "kaifang"
DEST = OUT_DIR / "cantonese.json"
MANIFEST = OUT_DIR / "manifest.json"
UPSTREAM = "https://kaifangcidian.com/xiazai/"


def write_manifest(*, copied: str | None = None) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": UPSTREAM,
        "license": "CC-BY-3.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_file": copied,
        "notes": "Place converted lexicon JSON at data/lexicon/raw/kaifang/cantonese.json",
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return MANIFEST


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="kaifang lexicon raw copy")
    parser.add_argument("--input", type=Path, required=True, help="Converted lexicon JSON")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.input, DEST)
    rel = str(DEST.relative_to(REPO_ROOT))
    write_manifest(copied=rel)
    print(f"Copied kaifang lexicon → {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
