from __future__ import annotations

from typing import List, Set, Tuple

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
