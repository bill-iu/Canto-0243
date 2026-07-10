#!/usr/bin/env python3
"""Copy guide-example rows from full lyrics.db into tests/fixtures/lyrics.db."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.patch_lou_dou_readings import patch_lyrics_db

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "lyrics.db"
SOURCE = REPO_ROOT / "lyrics.db"

# ponytail: minimal set for scripts/check_guide_examples five zero-result regressions
GUIDE_CHARS = frozenset({
    "潦", "困", "倒", "窮", "窮困潦倒",
    "開心", "苦悶", "不快",
    "你", "我",
    "與", "生", "死",
    "生死", "是非", "男女", "天地", "夫妻", "父母", "父子", "兄弟",
    "生與死", "天與地", "男與女", "父與子",
    "兄與弟", "夫與婦", "妻與夫", "師與徒", "父與母", "公與婆",
    # jyutping_lookup self-check (nei hou / ming4 baak6)
    "你好", "明白",
    # plus-anchor guide parity (23+好 / 2+好3 / +門0)
    "弄不好", "十分好", "未諗好",
    "仲好講", "仲好咩", "仲好啦",
    "門牙", "門人",
    # jyutping-anchor guide parity (3+ngo4 / 3$漢4 / 23+o)
    "倒我米", "罕見", "下一個",
    # relation guide parity; 休／息 is a curated static synonym flank for ~與~.
    "愉快", "休", "息", "休息", "休與息",
})


def _copy_rows(src: Path, dest: Path) -> int:
    if not src.is_file():
        raise SystemExit(f"missing source db: {src}")
    if not dest.is_file():
        raise SystemExit(f"missing fixture db: {dest}")

    s = sqlite3.connect(src)
    d = sqlite3.connect(dest)
    inserted = 0
    for char in sorted(GUIDE_CHARS):
        rows = s.execute(
            "SELECT char, code, jyutping, initials, finals, length FROM words WHERE char = ?",
            (char,),
        ).fetchall()
        for row in rows:
            exists = d.execute(
                "SELECT 1 FROM words WHERE char = ? AND jyutping = ? LIMIT 1",
                (row[0], row[2]),
            ).fetchone()
            if exists:
                continue
            next_id = d.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM words").fetchone()[0]
            d.execute(
                "INSERT INTO words (id, char, code, jyutping, initials, finals, length) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_id, *row),
            )
            inserted += 1
    d.commit()
    s.close()
    d.close()
    return inserted


def main() -> int:
    inserted = _copy_rows(SOURCE, FIXTURE)
    patched = patch_lyrics_db(FIXTURE)
    print(f"fixture guide patch: inserted {inserted} row(s), lou_dou {patched} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
