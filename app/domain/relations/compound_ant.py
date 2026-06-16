"""反義複合（!!）— curated 列表 ∩ 詞庫。"""

from __future__ import annotations

from typing import FrozenSet

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.lexicon.compound_antonyms import load_compound_antonyms


def search_compound_ant(
    db: Session,
    *,
    rhyme_char: str | None = None,
    width: int = 2,
) -> FrozenSet[str]:
    """!! 查詢候選：curated 反義複合字面；可選韻錨縮窄（如 !!你）。"""
    compounds = frozenset(ch for ch in load_compound_antonyms() if len(ch) == width)
    if not rhyme_char or width != 2:
        return compounds
    return narrow_compound_syn_literals(
        compounds, width=width, rhyme_char=rhyme_char, db=db
    )


__all__ = ["search_compound_ant"]
