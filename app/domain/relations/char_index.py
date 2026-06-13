from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.word import Word


def get_char_to_ids(db: Session) -> Dict[str, List[int]]:
    mapping: Dict[str, List[int]] = {}
    for wid, ch in db.query(Word.id, Word.char).all():
        if not ch:
            continue
        mapping.setdefault(ch, []).append(int(wid))
    return mapping


def get_char_to_primary_id(db: Session) -> Dict[str, int]:
    """One primary word id per 字面 (minimum id) for relation writes."""
    mapping = get_char_to_ids(db)
    return {ch: min(ids) for ch, ids in mapping.items() if ids}
