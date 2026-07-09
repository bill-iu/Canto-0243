"""填詞連接詞複合（!{連接}!／~{連接}~）— ADR-0053：詞庫 ∪ 合成 + syn/ant 互斥。"""

from __future__ import annotations

from typing import Dict, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.models.word import Word
from app.services._generated.fillword_connectives import FILLWORD_CONNECTIVES

# ponytail: guide／essay 常見填詞連接詞三字詞 — ensure 入庫（CONTEXT § 連接詞複合查詢）
CONNECTIVE_LITERAL_SEEDS: dict[str, tuple[str, ...]] = {
    "與": ("生與死", "天與地", "男與女", "父與子"),
}

# Lexicon flank tiers 0–2; synthetic always ranks after
TIER_CONNECTIVE_SYNTH = 3
# First-hit cost: cap synth + process cache for full result map
CONNECTIVE_SYNTH_CAP = 500

# (compound_kind, connective, rhyme_char|None) → tiers
_connective_result_cache: dict[Tuple[str, str, Optional[str]], Dict[str, int]] = {}


def reset_connective_compound_cache_for_tests() -> None:
    global _connective_result_cache
    _connective_result_cache = {}


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


def exclusive_two_char_tiers(
    primary: Dict[str, int],
    opposite: Dict[str, int],
    kind: Literal["syn", "ant"],
) -> Dict[str, int]:
    """Strict mutual exclusion with ant-wins: syn drops ant pairs; ant keeps full primary."""
    if kind == "ant":
        return dict(primary)
    return {w: t for w, t in primary.items() if w not in opposite}


def _three_char_with_connective(db: Session, connective: str) -> set[str]:
    """SQL-narrow to length-3 with fixed middle connective (SQLite LIKE `_連_`)."""
    pattern = f"_{connective}_"
    rows = (
        db.query(Word.char)
        .filter(Word.length == 3, Word.char.like(pattern))
        .distinct()
        .all()
    )
    return {row[0] for row in rows if row[0] and len(row[0]) == 3 and row[0][1] == connective}


def search_connective_compound(
    db: Session,
    *,
    compound_kind: Literal["syn", "ant"],
    connective: str,
    rhyme_char: str | None = None,
) -> Dict[str, int]:
    """!與!／~與~：詞庫三字 ∩ exclusive flank ∪ 合成缺席 A連B（cap + process cache）。"""
    if connective not in FILLWORD_CONNECTIVES:
        return {}

    cache_key = (compound_kind, connective, rhyme_char)
    hit = _connective_result_cache.get(cache_key)
    if hit is not None:
        return dict(hit)

    from app.domain.lexicon.port import default_word_inject_port
    from app.domain.relations.compound_ant import search_compound_ant
    from app.domain.relations.compound_syn import search_compound_syn

    inject = default_word_inject_port()
    for literal in CONNECTIVE_LITERAL_SEEDS.get(connective, ()):
        inject.ensure_word_rows(db, literal)

    # shared process caches inside search_compound_syn / ant
    syn_tiers = search_compound_syn(db)
    ant_tiers = search_compound_ant(db)
    if compound_kind == "ant":
        exclusive = exclusive_two_char_tiers(ant_tiers, syn_tiers, "ant")
    else:
        exclusive = exclusive_two_char_tiers(syn_tiers, ant_tiers, "syn")

    flank_tiers = _flank_tiers_from_two_char(exclusive)
    if not flank_tiers:
        _connective_result_cache[cache_key] = {}
        return {}

    tiers: Dict[str, int] = {}
    for w in _three_char_with_connective(db, connective):
        tier = flank_tiers.get((w[0], w[2]))
        if tier is not None:
            tiers[w] = tier

    synth_n = 0
    for (a, b), _flank in flank_tiers.items():
        if synth_n >= CONNECTIVE_SYNTH_CAP:
            break
        compound = f"{a}{connective}{b}"
        if compound in tiers:
            continue
        rows = inject.ensure_word_rows(db, compound)
        if rows:
            tiers[compound] = TIER_CONNECTIVE_SYNTH
            synth_n += 1

    if rhyme_char:
        allowed = narrow_compound_syn_literals(
            frozenset(tiers.keys()), width=3, rhyme_char=rhyme_char, db=db
        )
        tiers = {ch: tiers[ch] for ch in allowed if ch in tiers}

    _connective_result_cache[cache_key] = tiers
    return dict(tiers)


__all__ = [
    "CONNECTIVE_SYNTH_CAP",
    "FILLWORD_CONNECTIVES",
    "TIER_CONNECTIVE_SYNTH",
    "exclusive_two_char_tiers",
    "reset_connective_compound_cache_for_tests",
    "search_connective_compound",
]
