#!/usr/bin/env python3
"""Patch lyrics.db: 潦倒成語末字「潦」應讀 lou5，非 liu2/liu5。"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.utils.jyutping_codec import get_0243_code, split_jyutping

# ponytail: 只修末兩音節為 liu2/liu5 dou2 的 N字+潦倒 成語
_WRONG_LIU_TAIL = re.compile(r"liu[25] dou2$")


def corrected_lou_dou_jyutping(jyutping: str) -> str | None:
    text = (jyutping or "").strip()
    if not text or not _WRONG_LIU_TAIL.search(text):
        return None
    return _WRONG_LIU_TAIL.sub("lou5 dou2", text)


def patch_lyrics_db(db_path: Path | str) -> int:
    conn = sqlite3.connect(str(db_path))
    updated = 0
    for row_id, char, code, jyutping in conn.execute(
        "SELECT id, char, code, jyutping FROM words "
        "WHERE char LIKE '%潦倒' AND length(char) >= 3"
    ):
        fixed = corrected_lou_dou_jyutping(jyutping)
        if not fixed or fixed == jyutping:
            continue
        new_code = get_0243_code(fixed) or code
        initials, finals, tones = split_jyutping(fixed)
        conn.execute(
            "UPDATE words SET jyutping=?, code=?, initials=?, finals=?, tones=? WHERE id=?",
            (fixed, new_code, initials, finals, tones, row_id),
        )
        updated += 1
        print(f"{char}: {jyutping} -> {fixed} (code {code} -> {new_code})")
    conn.commit()
    conn.close()
    return updated


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    db = Path(args[0]) if args else REPO_ROOT / "lyrics.db"
    if not db.is_file():
        print(f"DB not found: {db}", file=sys.stderr)
        return 1
    n = patch_lyrics_db(db)
    print(f"updated {n} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
