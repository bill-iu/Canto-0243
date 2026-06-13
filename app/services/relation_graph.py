"""近反義關係圖：僅從 DB 取 raw tuple（無 ranking / enrichment）。"""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word
from app.repositories.word_relation_repo import fetch_bidirectional_relations


def fetch_relation_tuples(db: Session, query: str) -> List[Tuple]:
    """Return ORM/tuple rows from word_relations (bidirectional)."""
    q = query.strip()
    if not q:
        return []
    word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]
    return fetch_bidirectional_relations(db, word_ids)


__all__ = [
    "fetch_relation_tuples",
]
