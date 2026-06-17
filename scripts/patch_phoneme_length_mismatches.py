#!/usr/bin/env python3
"""修復詞條：CJK 字數與 finals／jyutping 音節槽不符（rime → pycantonese）。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.utils.jyutping_codec import get_0243_code, split_jyutping
from app.utils.json_helpers import load_json_list
from app.utils.reading_resolve import cjk_literal, phoneme_slot_count, resolve_repair_reading

_SKIP_CHAR = re.compile(r"…|\.\.\.")


def _needs_repair(char: str, jyutping: str, finals_raw) -> bool:
    if not char or _SKIP_CHAR.search(char):
        return False
    cjk = cjk_literal(char)
    if not cjk:
        return False
    slots = phoneme_slot_count(jyutping)
    finals = load_json_list(finals_raw)
    return slots != len(cjk) or len(finals) != len(cjk)


def scan_mismatches(conn) -> list[tuple]:
    rows = []
    for row_id, char, code, jyutping, finals in conn.execute(
        "SELECT id, char, code, jyutping, finals FROM words"
    ):
        if _needs_repair(char, jyutping or "", finals):
            rows.append((row_id, char, code, jyutping or "", finals))
    return rows


def patch_db(db_path: Path | str, *, dry_run: bool = True) -> dict:
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    mismatches = scan_mismatches(conn)
    fixed = 0
    skipped = 0
    samples: list[str] = []

    for row_id, char, code, old_jyut, _ in mismatches:
        ent = resolve_repair_reading(char)
        if not ent or not ent.jyutping:
            skipped += 1
            continue
        new_jyut = ent.jyutping
        new_code = ent.code or get_0243_code(new_jyut) or code
        initials, finals, tones = split_jyutping(new_jyut)
        if len(samples) < 20:
            samples.append(f"{char}: {old_jyut!r} -> {new_jyut!r} (code {code!r} -> {new_code!r})")
        if not dry_run:
            conn.execute(
                "UPDATE words SET jyutping=?, code=?, initials=?, finals=?, tones=? WHERE id=?",
                (new_jyut, new_code, initials, finals, tones, row_id),
            )
        fixed += 1

    if not dry_run:
        conn.commit()
    conn.close()
    return {
        "mismatches": len(mismatches),
        "fixed": fixed,
        "skipped": skipped,
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
    report = patch_db(db, dry_run=not args.apply)
    mode = "dry-run" if report["dry_run"] else "applied"
    print(f"[{mode}] mismatches={report['mismatches']} fixed={report['fixed']} skipped={report['skipped']}")
    out = sys.stdout
    encoding = getattr(out, "encoding", None) or "utf-8"
    for line in report["samples"]:
        text = line.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
