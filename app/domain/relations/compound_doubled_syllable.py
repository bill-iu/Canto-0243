"""同音節疊字（$$）— 快照與查詢（CONTEXT § 同音節疊字查詢）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.models.word import Word
from app.services.word_serializer import get_word_jyutping, get_word_text

_snapshot: Optional["DoubledSyllableSnapshot"] = None
_literals_cache: Optional[Dict[str, int]] = None


@dataclass(frozen=True)
class DoubledSyllableSnapshot:
    literals: FrozenSet[str]


def reset_doubled_syllable_snapshot_for_tests() -> None:
    global _snapshot, _literals_cache
    _snapshot = None
    _literals_cache = None


def _syllable_letters(token: str) -> str:
    return re.sub(r"[1-6]$", "", (token or "").lower())


def row_has_doubled_syllables(jyutping: str) -> bool:
    parts = (jyutping or "").split()
    if len(parts) != 2:
        return False
    left, right = _syllable_letters(parts[0]), _syllable_letters(parts[1])
    return bool(left) and left == right


def build_doubled_syllable_snapshot(db: Session) -> DoubledSyllableSnapshot:
    literals: set[str] = set()
    rows = db.query(Word.char, Word.jyutping).filter(Word.length == 2).all()
    for char, jyutping in rows:
        if not char or len(char) != 2:
            continue
        if row_has_doubled_syllables(jyutping or ""):
            literals.add(char)
    return DoubledSyllableSnapshot(literals=frozenset(literals))


def ensure_doubled_syllable_snapshot(db: Session) -> DoubledSyllableSnapshot:
    global _snapshot
    if _snapshot is None:
        _snapshot = build_doubled_syllable_snapshot(db)
    return _snapshot


def search_doubled_syllable(
    db: Session,
    *,
    rhyme_char: str | None = None,
    width: int = 2,
) -> Dict[str, int]:
    """$$ 查詢候選：字面 → tier（0）；可選韻錨縮窄。"""
    global _literals_cache
    if width != 2:
        return {}
    if _literals_cache is None:
        snap = ensure_doubled_syllable_snapshot(db)
        _literals_cache = {ch: 0 for ch in snap.literals}
    tiers = _literals_cache
    if not rhyme_char:
        return dict(tiers)
    allowed = narrow_compound_syn_literals(
        frozenset(tiers.keys()), width=width, rhyme_char=rhyme_char, db=db
    )
    return {ch: tiers[ch] for ch in allowed if ch in tiers}


__all__ = [
    "DoubledSyllableSnapshot",
    "build_doubled_syllable_snapshot",
    "ensure_doubled_syllable_snapshot",
    "reset_doubled_syllable_snapshot_for_tests",
    "row_has_doubled_syllables",
    "search_doubled_syllable",
]
