"""雙聲疊韻字（$$…）— 快照與查詢（CONTEXT § 雙聲疊韻字查詢）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.models.word import Word

MIN_DOUBLED_WIDTH = 2
MAX_DOUBLED_WIDTH = 4

_snapshots_by_width: Optional[Dict[int, FrozenSet[str]]] = None


@dataclass(frozen=True)
class DoubledSyllableSnapshot:
    literals_by_width: Dict[int, FrozenSet[str]]


def reset_doubled_syllable_snapshot_for_tests() -> None:
    global _snapshots_by_width
    _snapshots_by_width = None


def _syllable_letters(token: str) -> str:
    return re.sub(r"[1-6]$", "", (token or "").lower())


def row_has_uniform_syllable_letters(jyutping: str, width: int) -> bool:
    parts = (jyutping or "").split()
    if len(parts) != width:
        return False
    letters = [_syllable_letters(p) for p in parts]
    return bool(letters[0]) and all(x == letters[0] for x in letters)


def row_has_doubled_syllables(jyutping: str) -> bool:
    return row_has_uniform_syllable_letters(jyutping, MIN_DOUBLED_WIDTH)


def build_doubled_syllable_snapshot_for_width(db: Session, width: int) -> FrozenSet[str]:
    literals: set[str] = set()
    rows = db.query(Word.char, Word.jyutping).filter(Word.length == width).all()
    for char, jyutping in rows:
        if not char or len(char) != width:
            continue
        if row_has_uniform_syllable_letters(jyutping or "", width):
            literals.add(char)
    return frozenset(literals)


def build_doubled_syllable_snapshot(db: Session) -> DoubledSyllableSnapshot:
    by_width = {
        w: build_doubled_syllable_snapshot_for_width(db, w)
        for w in range(MIN_DOUBLED_WIDTH, MAX_DOUBLED_WIDTH + 1)
    }
    return DoubledSyllableSnapshot(literals_by_width=by_width)


def ensure_doubled_syllable_snapshot(db: Session) -> DoubledSyllableSnapshot:
    global _snapshots_by_width
    if _snapshots_by_width is None:
        snap = build_doubled_syllable_snapshot(db)
        _snapshots_by_width = snap.literals_by_width
    return DoubledSyllableSnapshot(literals_by_width=_snapshots_by_width)


def search_doubled_syllable(
    db: Session,
    *,
    rhyme_char: str | None = None,
    width: int = 2,
) -> Dict[str, int]:
    """雙聲疊韻字查詢候選：字面 → tier（0）；可選韻錨縮窄。"""
    if width < MIN_DOUBLED_WIDTH or width > MAX_DOUBLED_WIDTH:
        return {}
    snap = ensure_doubled_syllable_snapshot(db)
    tiers = {ch: 0 for ch in snap.literals_by_width.get(width, frozenset())}
    if not rhyme_char:
        return dict(tiers)
    allowed = narrow_compound_syn_literals(
        frozenset(tiers.keys()), width=width, rhyme_char=rhyme_char, db=db
    )
    return {ch: tiers[ch] for ch in allowed if ch in tiers}


__all__ = [
    "MAX_DOUBLED_WIDTH",
    "MIN_DOUBLED_WIDTH",
    "DoubledSyllableSnapshot",
    "build_doubled_syllable_snapshot",
    "build_doubled_syllable_snapshot_for_width",
    "ensure_doubled_syllable_snapshot",
    "reset_doubled_syllable_snapshot_for_tests",
    "row_has_doubled_syllables",
    "row_has_uniform_syllable_letters",
    "search_doubled_syllable",
]