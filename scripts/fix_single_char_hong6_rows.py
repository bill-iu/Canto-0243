"""Fix 行 code=2 hong6→hang6; delete code=9 hong6 行／巷 單字列。"""
from __future__ import annotations

import argparse

from app.database import SessionLocal
from app.models.word import Word
from app.utils.jyutping_codec import get_0243_code, split_jyutping

_TARGET_CHAR = "行"


def _apply_jyutping(row: Word, jyutping: str) -> None:
    row.jyutping = jyutping
    row.code = get_0243_code(jyutping)
    initials, finals, _tones = split_jyutping(jyutping)
    row.initials = initials
    row.finals = finals
    if row.length is None or row.length == 0:
        row.length = len(row.char or "")


def fix_db(*, dry_run: bool = True) -> dict[str, int]:
    db = SessionLocal()
    stats = {"hang6_fix": 0, "hong4_fix": 0, "deleted_code9_hong6": 0}
    try:
        q = db.query(Word).filter(
            Word.char == _TARGET_CHAR,
            Word.code == "2",
            Word.jyutping == "hong6",
        )
        for row in q.all():
            if dry_run:
                print(f"would fix id={row.id} 行: hong6 -> hang6 (code 2)")
            else:
                _apply_jyutping(row, "hang6")
            stats["hang6_fix"] += 1

        q0 = db.query(Word).filter(
            Word.char == _TARGET_CHAR,
            Word.code == "0",
            Word.jyutping == "hong6",
        )
        for row in q0.all():
            if dry_run:
                print(f"would fix id={row.id} 行: hong6 -> hong4 (code 0)")
            else:
                _apply_jyutping(row, "hong4")
            stats["hong4_fix"] += 1

        del_q = db.query(Word).filter(Word.code == "9", Word.jyutping == "hong6")
        for row in del_q.all():
            if dry_run:
                print(f"would delete id={row.id} {row.char!r} code=9 hong6")
            else:
                db.delete(row)
            stats["deleted_code9_hong6"] += 1

        if not dry_run:
            db.commit()
        return stats
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    stats = fix_db(dry_run=not args.apply)
    print(stats)


if __name__ == "__main__":
    main()
