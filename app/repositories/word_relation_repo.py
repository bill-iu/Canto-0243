from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word, WordRelation

RELATION_TYPES = ("syn", "ant", "semantic_related")


def fetch_bidirectional_relations(db: Session, word_ids: List[int]) -> List[Tuple]:
    if not word_ids:
        return []
    forward = (
        db.query(
            WordRelation.relation_type,
            Word.char,
            WordRelation.source,
            WordRelation.score,
            Word.jyutping,
            Word.code,
            WordRelation.group_codes,
        )
        .join(Word, WordRelation.related_id == Word.id)
        .filter(WordRelation.word_id.in_(word_ids))
        .filter(WordRelation.relation_type.in_(RELATION_TYPES))
    )
    backward = (
        db.query(
            WordRelation.relation_type,
            Word.char,
            WordRelation.source,
            WordRelation.score,
            Word.jyutping,
            Word.code,
            WordRelation.group_codes,
        )
        .join(Word, WordRelation.word_id == Word.id)
        .filter(WordRelation.related_id.in_(word_ids))
        .filter(WordRelation.relation_type.in_(RELATION_TYPES))
    )
    return forward.union(backward).all()


def load_db_char_set(db: Session) -> Set[str]:
    return {r[0] for r in db.query(Word.char).distinct().all() if r[0]}


_IN_DB_LOOKUP_CHUNK = 500


def chars_present_in_db(db: Session, chars: Iterable[str]) -> Set[str]:
    """Return which literals from *chars* exist in words (batch, not full-table)."""
    unique = {c for c in chars if c}
    if not unique:
        return set()
    present: Set[str] = set()
    ordered = list(unique)
    for start in range(0, len(ordered), _IN_DB_LOOKUP_CHUNK):
        chunk = ordered[start : start + _IN_DB_LOOKUP_CHUNK]
        rows = db.query(Word.char).filter(Word.char.in_(chunk)).all()
        present.update(r[0] for r in rows if r[0])
    return present
