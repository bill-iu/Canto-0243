"""填詞連接詞複合 — ADR-0053 混合 + ADR-0054 Portable 請求路徑零寫庫。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.models.word import Word
from app.services._generated.fillword_connectives import FILLWORD_CONNECTIVES

CONNECTIVE_LITERAL_SEEDS: dict[str, tuple[str, ...]] = {
    "與": ("生與死", "天與地", "男與女", "父與子"),
}

TIER_CONNECTIVE_SYNTH = 3
CONNECTIVE_SYNTH_CAP = 500

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
    if kind == "ant":
        return dict(primary)
    return {w: t for w, t in primary.items() if w not in opposite}


def _three_char_with_connective(db: Session, connective: str) -> set[str]:
    pattern = f"_{connective}_"
    rows = (
        db.query(Word.char)
        .filter(Word.length == 3, Word.char.like(pattern))
        .distinct()
        .all()
    )
    return {row[0] for row in rows if row[0] and len(row[0]) == 3 and row[0][1] == connective}


def compose_transient_word(text: str) -> Optional[SimpleNamespace]:
    """Memory-only row (ADR-0054) — syllable compose / static lexicon, no DB write."""
    from app.domain.lexicon.admission import resolve_admission
    from app.utils.jyutping_codec import split_jyutping

    text = (text or "").strip()
    if len(text) < 2:
        return None
    adm = resolve_admission(text)
    if not adm.entries:
        return None
    ent = adm.entries[0]
    jyut = (ent.jyutping or "").strip()
    if not jyut:
        return None
    try:
        initials, finals, _tones = split_jyutping(jyut)
    except Exception:
        initials, finals = [], []
    return SimpleNamespace(
        id=None,
        char=text,
        code=ent.code or "",
        jyutping=jyut,
        initials=initials,
        finals=finals,
        length=len(text),
    )


def search_connective_compound(
    db: Session,
    *,
    compound_kind: Literal["syn", "ant"],
    connective: str,
    rhyme_char: str | None = None,
) -> Dict[str, int]:
    """詞庫三字 ∩ exclusive flank ∪ 合成字面（tiers only；上榜由 CandidateSource 記憶體合成）。"""
    if connective not in FILLWORD_CONNECTIVES:
        return {}

    cache_key = (compound_kind, connective, rhyme_char)
    hit = _connective_result_cache.get(cache_key)
    if hit is not None:
        return dict(hit)

    from app.domain.relations.compound_ant import search_compound_ant
    from app.domain.relations.compound_syn import search_compound_syn

    # Seeds: mark as curated tier if present in DB or composable — never ensure_word_rows
    seed_set = set(CONNECTIVE_LITERAL_SEEDS.get(connective, ()))

    syn_tiers = search_compound_syn(db)
    ant_tiers = search_compound_ant(db)
    if compound_kind == "ant":
        exclusive = exclusive_two_char_tiers(ant_tiers, syn_tiers, "ant")
    else:
        exclusive = exclusive_two_char_tiers(syn_tiers, ant_tiers, "syn")

    flank_tiers = _flank_tiers_from_two_char(exclusive)
    if not flank_tiers and not seed_set:
        _connective_result_cache[cache_key] = {}
        return {}

    tiers: Dict[str, int] = {}
    for w in _three_char_with_connective(db, connective):
        tier = flank_tiers.get((w[0], w[2]))
        if tier is not None:
            tiers[w] = tier

    for seed in seed_set:
        if len(seed) == 3 and seed[1] == connective:
            pair_tier = flank_tiers.get((seed[0], seed[2]))
            if pair_tier is not None:
                tiers.setdefault(seed, pair_tier)
            elif compound_kind == "ant":
                # guide seeds are typically ant flanks even if graph lagging
                tiers.setdefault(seed, 0)

    synth_n = 0
    for (a, b), _flank in flank_tiers.items():
        if synth_n >= CONNECTIVE_SYNTH_CAP:
            break
        compound = f"{a}{connective}{b}"
        if compound in tiers:
            continue
        # Admit only if we can compose a reading without DB write
        if compose_transient_word(compound) is None:
            continue
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
    "compose_transient_word",
    "exclusive_two_char_tiers",
    "reset_connective_compound_cache_for_tests",
    "search_connective_compound",
]
