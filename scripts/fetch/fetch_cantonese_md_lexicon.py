"""Extract daimaruhk/Cantonese.md term/answer → lexicon JSON (missing-literal only).

Default: download main zip, keep only literals absent from lyrics.db (or --all),
len 1–12, valid word reading. Does NOT rebuild lyrics.db.

Usage:
  PYTHONIOENCODING=utf-8 python scripts/fetch/fetch_cantonese_md_lexicon.py
  PYTHONIOENCODING=utf-8 python scripts/fetch/fetch_cantonese_md_lexicon.py --db lyrics.db
  PYTHONIOENCODING=utf-8 python scripts/fetch/fetch_cantonese_md_lexicon.py --all
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import is_valid_term, normalize_literal  # noqa: E402
from app.utils.jyutping_codec import get_0243_code  # noqa: E402
from ingest.lexicon_validate import normalize_lexicon_candidate  # noqa: E402

ARCHIVE = "https://codeload.github.com/daimaruhk/Cantonese.md/zip/refs/heads/main"
OUT_DIR = ROOT / "data" / "lexicon" / "raw" / "cantonese_md"
OUT_JSON = OUT_DIR / "lexicon.json"
OUT_META = OUT_DIR / "manifest.json"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
KV_RE = re.compile(
    r"^(term|termJyutping|answer|answerJyutping):\s*(.*)$", re.M
)


def _load_rows(blob: bytes) -> list[dict[str, str]]:
    zf = zipfile.ZipFile(io.BytesIO(blob))
    rows: list[dict[str, str]] = []
    for name in zf.namelist():
        if "/src/contents/" not in name.replace("\\", "/") or not name.endswith(".md"):
            continue
        text = zf.read(name).decode("utf-8")
        m = FM_RE.search(text)
        if not m:
            continue
        d: dict[str, str] = {}
        for k, v in KV_RE.findall(m.group(1)):
            d[k] = v.strip().strip("\"'")
        if d.get("term"):
            rows.append(d)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    ap.add_argument(
        "--all",
        action="store_true",
        help="Keep all valid readings (not only missing literals)",
    )
    ap.add_argument("--url", default=ARCHIVE)
    args = ap.parse_args()

    req = urllib.request.Request(args.url, headers={"User-Agent": "Canto-0243-fetch"})
    print(f"download {args.url}")
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    rows = _load_rows(blob)
    print(f"parsed entries {len(rows)}")

    have: set[str] = set()
    if not args.all:
        if not args.db.is_file():
            print(f"missing db {args.db}; use --all or pass --db", file=sys.stderr)
            return 1
        con = sqlite3.connect(args.db)
        have = {r[0] for r in con.execute("select distinct char from words")}
        print(f"db literals {len(have)}")

    # one best reading per literal (first wins; term before answer if same pass order)
    by_char: dict[str, dict[str, str]] = {}
    skipped = {
        "empty": 0,
        "invalid_term": 0,
        "in_db": 0,
        "bad_reading": 0,
        "dup": 0,
    }
    for r in rows:
        for lit_k, jp_k in (("term", "termJyutping"), ("answer", "answerJyutping")):
            raw_lit = r.get(lit_k, "")
            raw_jp = r.get(jp_k, "")
            lit = normalize_literal(raw_lit) or raw_lit.strip()
            jp = raw_jp.strip()
            if not lit or not jp:
                skipped["empty"] += 1
                continue
            if not is_valid_term(lit) or not (1 <= len(lit) <= 12):
                skipped["invalid_term"] += 1
                continue
            if not args.all and lit in have:
                skipped["in_db"] += 1
                continue
            norm = normalize_lexicon_candidate(lit, jp)
            if not norm:
                skipped["bad_reading"] += 1
                continue
            char, jy, code = norm
            if not code:
                code = get_0243_code(jy) or ""
            if not code:
                skipped["bad_reading"] += 1
                continue
            if char in by_char:
                skipped["dup"] += 1
                continue
            by_char[char] = {
                "char": char,
                "jyutping": jy,
                "code": code,
            }

    items = [by_char[k] for k in sorted(by_char)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    meta = {
        "source": "https://github.com/daimaruhk/Cantonese.md",
        "license": "CC0-1.0",
        "attribution": "daimaruhk/Cantonese.md (src/contents/; CC0)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "archive_url": args.url,
        "filter": "all_valid" if args.all else "missing_literal_vs_db",
        "db": None if args.all else str(args.db.as_posix()),
        "n_entries_parsed": len(rows),
        "n_lexicon_rows": len(items),
        "skipped": skipped,
        "raw_file": "lexicon.json",
        "notes": (
            "Only term/answer + Jyutping; no explanations. "
            "Wire via data/lexicon/sources.yaml id=cantonese_md. "
            "Does not rebuild lyrics.db — run `python -m ingest build-db` when ready."
        ),
    }
    OUT_META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT_JSON.relative_to(ROOT)} n={len(items)}")
    print(f"wrote {OUT_META.relative_to(ROOT)}")
    print("skipped", skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
