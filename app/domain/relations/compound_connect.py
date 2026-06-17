"""填詞連接詞複合（!{連接}!／~{連接}~）。"""

from __future__ import annotations

from typing import Dict, Literal

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.models.word import Word

FILLWORD_CONNECTIVES = frozenset("與和或共同及跟而且並向")


def _flank_tiers_from_two_char(two_char_tiers: Dict[str, int]) -> Dict[tuple[str, str], int]:
    out: Dict[tuple[str, str], int] = {}
    for w, tier in two_char_tiers.items():
        if len(w) != 2:
            continue
        a, b = w[0], w[1]
        for pair in ((a, b), (b, a)):
            prev = out.get(pair)
            out[pair] = tier if prev is None else min(prev, tier)
    return out


def _three_char_literals(db: Session) -> set[str]:
    rows = db.query(Word.char).filter(Word.length == 3).distinct().all()
    return {row[0] for row in rows if row[0] and len(row[0]) == 3}


def search_connective_compound(
    db: Session,
    *,
    compound_kind: Literal["syn", "ant"],
    connective: str,
    rhyme_char: str | None = None,
) -> Dict[str, int]:
    """!與!／~與~：三字詞庫掃描，首尾沿用 !!／~~ 候選規則。"""
    if connective not in FILLWORD_CONNECTIVES:
        return {}

    if compound_kind == "ant":
        from app.domain.relations.compound_ant import search_compound_ant

        two_char_tiers = search_compound_ant(db)
    else:
        from app.domain.relations.compound_syn import search_compound_syn

        two_char_tiers = search_compound_syn(db)

    flank_tiers = _flank_tiers_from_two_char(two_char_tiers)
    if not flank_tiers:
        return {}

    tiers: Dict[str, int] = {}
    for w in _three_char_literals(db):
        if len(w) != 3 or w[1] != connective:
            continue
        tier = flank_tiers.get((w[0], w[2]))
        if tier is None:
            continue
        tiers[w] = tier

    if not rhyme_char:
        return tiers
    allowed = narrow_compound_syn_literals(
        frozenset(tiers.keys()), width=3, rhyme_char=rhyme_char, db=db
    )
    return {ch: tiers[ch] for ch in allowed if ch in tiers}


__all__ = ["FILLWORD_CONNECTIVES", "search_connective_compound"]
