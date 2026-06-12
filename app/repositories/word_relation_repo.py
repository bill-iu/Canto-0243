from __future__ import annotations

from typing import List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word, WordRelation
from app.services.syn_ant_ranking import final_score, parse_group_codes

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


def normalize_relation_row(
    rtype: str,
    rchar: str,
    source,
    score,
    jyutping,
    code,
    group_codes_raw,
    *,
    query: str,
    db_char_set: Set[str],
) -> dict | None:
    if not rchar or rchar == query:
        return None
    in_db = rchar in db_char_set
    group_codes = parse_group_codes(group_codes_raw)
    return {
        "char": rchar,
        "relation": rtype,
        "source": source or "word_relations",
        "score": score,
        "in_db": in_db,
        "jyutping": jyutping or "",
        "code": code or "",
        "group_codes": group_codes,
        "_group_codes": group_codes,
        "_sort": final_score(source=source, confidence=score, in_db=in_db),
    }
