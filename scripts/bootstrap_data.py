#!/usr/bin/env python3
"""
One-command fetch for optional third-party datasets (Canto-0243 v1).

Downloads runtime/ingest inputs that are NOT bundled in git. Essay corpus and
project-curated files ship with the repo. See THIRD_PARTY_NOTICES.md.

Usage:
  pip install -r requirements-dev.txt   # cilin export only
  python scripts/bootstrap_data.py
  python scripts/bootstrap_data.py --dry-run
  python scripts/bootstrap_data.py --skip-cilin
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

NOTICE = """
=== Third-party data notice ===
By running this script you fetch datasets governed by their upstream licenses
(see THIRD_PARTY_NOTICES.md). Canto-0243 program code is under Canto-0243
License; fetched files remain under their respective terms.
"""


def _run(cmd: list[str], *, dry_run: bool, label: str) -> int:
    print(f"\n--- {label} ---")
    if dry_run:
        print("  ", " ".join(cmd))
        return 0
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(result.returncode or 0)


def _cilin_available() -> bool:
    return importlib.util.find_spec("cilin") is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch optional Canto-0243 datasets")
    parser.add_argument("--dry-run", action="store_true", help="Print steps only")
    parser.add_argument("--skip-cilin", action="store_true", help="Skip cilin export (needs pip cilin)")
    parser.add_argument("--update-essay", action="store_true", help="Re-download essay corpus")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print(NOTICE.strip())

    steps: list[tuple[str, list[str]]] = [
        ("rime char.csv (CC BY 4.0)", [PYTHON, "scripts/fetch/fetch_rime_data.py"]),
        ("guotong thesaurus (Anti-996)", [PYTHON, "scripts/fetch/fetch_guotong_thesaurus.py"]),
        ("words.hk wordslist manifest", [PYTHON, "scripts/fetch/fetch_words_hk_wordslist.py"]),
    ]
    if args.update_essay:
        steps.append(
            ("essay frequency corpus (CC BY 4.0)", [PYTHON, "scripts/fetch/fetch_essay_data.py"])
        )
    if not args.skip_cilin:
        steps.append(("cilin leaf export (MIT upstream)", [PYTHON, "scripts/fetch/fetch_cilin_data.py"]))

    failed = 0
    for label, cmd in steps:
        if "fetch_cilin_data" in cmd[-1] and not args.dry_run and not _cilin_available():
            print(f"\n--- {label} ---")
            print("  SKIP: pip install cilin opencc-python-reimplemented  (requirements-dev.txt)")
            failed += 1
            continue
        failed += _run(cmd, dry_run=args.dry_run, label=label) != 0

    print("\n=== Next steps (maintainer) ===")
    print("  1. words.hk / 開放詞典: fetch or place raw JSON (see data/lexicon/sources.yaml)")
    print("  2. Full lexicon rebuild (per-source manifest, no CC-Canto):")
    print("       python -m ingest build-db")
    print("  3. Relations: python -m ingest normalize --source current_static && python -m ingest build-relations")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
