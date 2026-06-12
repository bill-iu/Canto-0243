from __future__ import annotations

from typing import Set, Tuple

from sqlalchemy.orm import Session, aliased

from app.models.word import Word, WordRelation
from app.services.syn_ant_thesaurus_adapter import fetch_static_char_ant_pairs


def build_char_antonym_pairs(db: Session) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    w1 = aliased(Word)
    w2 = aliased(Word)
    for a, b in (
        db.query(w1.char, w2.char)
        .join(WordRelation, WordRelation.word_id == w1.id)
        .join(w2, WordRelation.related_id == w2.id)
        .filter(WordRelation.relation_type == "ant")
        .all()
    ):
        if not a or not b or len(a) != 1 or len(b) != 1:
            continue
        pairs.add((a, b))
        pairs.add((b, a))

    pairs.update(fetch_static_char_ant_pairs())
    return pairs
