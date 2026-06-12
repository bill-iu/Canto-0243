#!/usr/bin/env python3
"""
Export 同義詞詞林 (Cilin extended) leaf synonym groups to data/cilin/new_cilin.txt.

Uses Cilin(trad=True) so all terms are Traditional Chinese (OpenCC s2t), matching:
  https://github.com/liao961120/cilin

Only level-5 leaf codes (e.g. Aa01A01=, Ca01B01=) are exported — category tags are omitted.

Usage:
  pip install cilin opencc-python-reimplemented
  python scripts/fetch/fetch_cilin_data.py
  python -m ingest ingest-cilin --direct --dedupe-existing
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_PATH = REPO_ROOT / "data" / "cilin" / "new_cilin.txt"

from ingest.cilin_leaf import patch_opencc_for_cilin


def export_new_cilin(trad: bool = True) -> list[str]:
    from ingest.cilin_leaf import export_leaf_lines_from_api

    return export_leaf_lines_from_api(trad=trad)


def verify_sample(trad: bool = True) -> None:
    patch_opencc_for_cilin()
    from cilin import Cilin

    c = Cilin(trad=trad)
    print(f"[verify] get_tag('A') = {c.get_tag('A')!r}")
    print(f"[verify] get_tag('Aa') = {c.get_tag('Aa')!r}")
    print(f"[verify] get_tag('Aa01') = {c.get_tag('Aa01')!r}")
    members = sorted(c.get_members("Ca01B01="))
    print(f"[verify] get_members('Ca01B01=') = {members}")
    split_a = c.category_split(level=1)
    print(f"[verify] category_split(1) keys = {sorted(split_a.keys())}")


def assert_traditional_samples(lines: list[str]) -> None:
    """Fail fast if export is not Traditional Chinese."""
    joined = "\n".join(lines)
    required = ("舊曆", "農曆", "陰曆", "快樂", "開心")
    missing = [w for w in required if w not in joined]
    if missing:
        raise RuntimeError(f"Traditional sample words missing from export: {missing}")
    if "旧历" in joined or "农历" in joined:
        raise RuntimeError("Export still contains Simplified Chinese forms (e.g. 旧历/农历)")
    from ingest.cilin_leaf import is_cilin_leaf_code

    bad = [ln.split()[0] for ln in lines if ln.strip() and not is_cilin_leaf_code(ln.split()[0])]
    if bad:
        raise RuntimeError(f"Non-leaf codes in export: {bad[:5]}")


def main() -> int:
    try:
        lines = export_new_cilin(trad=True)
        assert_traditional_samples(lines)
    except ImportError:
        print("Missing dependency. Run: pip install cilin opencc-python-reimplemented", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} leaf synonym lines ({OUT_PATH.stat().st_size // 1024} KB) -> {OUT_PATH}")

    try:
        verify_sample(trad=True)
    except Exception as exc:
        print(f"[verify] warning: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
