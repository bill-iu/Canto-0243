"""同音異讀字面索引（啟動預載；CONTEXT § 同音異讀查詢）。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word

ReadingRow = Tuple[str, str]
_index: Optional[Dict[str, List[ReadingRow]]] = None


def reset_heteronym_index_for_tests() -> None:
    global _index
    _index = None


def build_heteronym_index(db: Session) -> Dict[str, List[ReadingRow]]:
    buckets: Dict[str, List[ReadingRow]] = {}
    for char, code, jyutping in db.query(Word.char, Word.code, Word.jyutping).all():
        if not char or not jyutping:
            continue
        buckets.setdefault(char, []).append((code or "", jyutping))
    out: Dict[str, List[ReadingRow]] = {}
    for char, readings in buckets.items():
        distinct = {jp for _, jp in readings}
        if len(distinct) < 2:
            continue
        out[char] = readings
    return out


def ensure_heteronym_index(db: Session) -> Dict[str, List[ReadingRow]]:
    global _index
    if _index is None:
        _index = build_heteronym_index(db)
    return _index


__all__ = [
    "ReadingRow",
    "build_heteronym_index",
    "ensure_heteronym_index",
    "reset_heteronym_index_for_tests",
]
