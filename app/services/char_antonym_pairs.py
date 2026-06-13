from __future__ import annotations

from typing import Optional, Set, Tuple

from sqlalchemy.orm import Session, aliased

from app.models.word import Word, WordRelation
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port


def _static_char_ant_pairs(thesaurus: ThesaurusPort) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    try:
        thesaurus.ensure_loaded()
        for ch, ant in thesaurus.iter_antonym_edges():
            if len(ch) != 1 or not ant or len(ant) != 1 or ant == ch:
                continue
            pairs.add((ch, ant))
            pairs.add((ant, ch))
    except Exception:
        pass
    return pairs


def build_char_antonym_pairs(
    db: Session,
    *,
    thesaurus: Optional[ThesaurusPort] = None,
) -> Set[Tuple[str, str]]:
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

    port = thesaurus or default_thesaurus_port()
    pairs.update(_static_char_ant_pairs(port))
    return pairs
