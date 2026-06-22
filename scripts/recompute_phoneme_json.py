#!/usr/bin/env python3
"""批次重算 words.initials／finals／tones（split_jyutping；y- 韻核等 codec 變更後用）。"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.utils.jyutping_codec import split_jyutping


def recompute_phoneme_json(jyutping: str) -> tuple[str, str, str]:
    return split_jyutping(jyutping or "")


def needs_phoneme_recompute(
    jyutping: str,
    initials: str | None,
    finals: str | None,
    tones: str | None,
) -> bool:
    if not (jyutping or "").strip():
        return False
    new_initials, new_finals, new_tones = recompute_phoneme_json(jyutping)
    return (initials or "") != new_initials or (finals or "") != new_finals or (tones or "") != new_tones


def recompute_db(db_path: Path | str, *, dry_run: bool = True) -> dict:
    conn = sqlite3.connect(str(db_path))
    scanned = 0
    stale = 0
    updated = 0
    samples: list[str] = []

    for row_id, char, jyutping, initials, finals, tones in conn.execute(
        "SELECT id, char, jyutping, initials, finals, tones FROM words"
    ):
        scanned += 1
        if not needs_phoneme_recompute(jyutping or "", initials, finals, tones):
            continue
        stale += 1
        new_initials, new_finals, new_tones = recompute_phoneme_json(jyutping or "")
        if len(samples) < 20:
            samples.append(
                f"{char}: finals {finals!r} -> {new_finals!r} "
                f"(initials {initials!r} -> {new_initials!r})"
            )
        if not dry_run:
            conn.execute(
                "UPDATE words SET initials=?, finals=?, tones=? WHERE id=?",
                (new_initials, new_finals, new_tones, row_id),
            )
            updated += 1

    if not dry_run:
        conn.commit()
    conn.close()
    return {
        "scanned": scanned,
        "stale": stale,
        "updated": updated if not dry_run else 0,
        "dry_run": dry_run,
        "samples": samples,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", nargs="?", default=str(REPO_ROOT / "lyrics.db"))
    parser.add_argument("--apply", action="store_true", help="寫入 DB（預設 dry-run）")
    args = parser.parse_args(argv)
    db = Path(args.db)
    if not db.is_file():
        print(f"DB not found: {db}", file=sys.stderr)
        return 1
    report = recompute_db(db, dry_run=not args.apply)
    mode = "dry-run" if report["dry_run"] else "applied"
    print(
        f"[{mode}] scanned={report['scanned']} stale={report['stale']} "
        f"updated={report['updated']}"
    )
    out = sys.stdout
    encoding = getattr(out, "encoding", None) or "utf-8"
    for line in report["samples"]:
        text = line.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    assert needs_phoneme_recompute("zyu6", '["zy"]', '["u"]', "[6]")
    assert not needs_phoneme_recompute(
        "zyu6", *recompute_phoneme_json("zyu6"),
    )
    raise SystemExit(main())
