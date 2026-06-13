"""近義複合（~~）候選建構：curated + 同義素掃描 + 單字合成。"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, FrozenSet, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.graph import CharRelationGraph, default_char_relation_graph
from app.lexicon.compound_synonyms import load_compound_synonyms
from app.models.word import Word
from app.repositories.word_relation_repo import load_db_char_set
from app.services.essay_sort import default_word_sort_key

TIER_CURATED = 0
TIER_MORPHEME = 1
TIER_SYNTHESIZED = 2

DEFAULT_SYN_NEIGHBOR_K = 12

_cache: Optional["CompoundSynCache"] = None


@dataclass(frozen=True)
class CompoundSynCache:
    """啟動／首次查詢預算：curated 列表、同義素掃描集、詞庫 2 字字面全集。"""

    curated_literals: FrozenSet[str]
    morpheme_literals: FrozenSet[str]
    two_char_literals: FrozenSet[str]
    single_char_literals: FrozenSet[str]


def reset_compound_syn_cache_for_tests() -> None:
    global _cache
    _cache = None


def _char_sort_key(ch: str) -> tuple:
    return default_word_sort_key(SimpleNamespace(char=ch, code="", jyutping=""))


def _top_k_syn_neighbors(graph: CharRelationGraph, char: str, k: int) -> list[str]:
    neighbors = graph.direct_syn_neighbors(char)
    if not neighbors:
        return []
    ordered = sorted(neighbors, key=_char_sort_key)
    return ordered[:max(0, k)]


def _scan_morpheme_compounds(
    db: Session,
    graph: CharRelationGraph,
    two_char_literals: Set[str],
) -> Set[str]:
    ant_pairs = graph.direct_ant_oriented_pairs()
    out: Set[str] = set()
    for compound in two_char_literals:
        if len(compound) != 2:
            continue
        a, b = compound[0], compound[1]
        if a == b:
            continue
        if (a, b) in ant_pairs:
            continue
        neighbors_a = graph.direct_syn_neighbors(a)
        if b in neighbors_a:
            out.add(compound)
    return out


def build_compound_syn_cache(db: Session) -> CompoundSynCache:
    membership = load_db_char_set(db)
    graph = default_char_relation_graph(db, membership=membership)

    two_char_rows = db.query(Word.char).filter(Word.length == 2).distinct().all()
    two_char_literals = {row[0] for row in two_char_rows if row[0] and len(row[0]) == 2}

    single_rows = db.query(Word.char).filter(Word.length == 1).distinct().all()
    single_char_literals = {row[0] for row in single_rows if row[0] and len(row[0]) == 1}

    curated_file = [ch for ch in load_compound_synonyms() if ch in two_char_literals]
    morpheme = _scan_morpheme_compounds(db, graph, two_char_literals)

    return CompoundSynCache(
        curated_literals=frozenset(curated_file),
        morpheme_literals=frozenset(morpheme),
        two_char_literals=frozenset(two_char_literals),
        single_char_literals=frozenset(single_char_literals),
    )


def ensure_compound_syn_cache(db: Session) -> CompoundSynCache:
    global _cache
    if _cache is None:
        _cache = build_compound_syn_cache(db)
    return _cache


def synthesize_compound_literals(
    cache: CompoundSynCache,
    graph: CharRelationGraph,
    *,
    k: int = DEFAULT_SYN_NEIGHBOR_K,
) -> Set[str]:
    """查詢時單字近義合成（top‑K）；只回傳詞庫已有 2 字詞。"""
    out: Set[str] = set()
    base = cache.curated_literals | cache.morpheme_literals
    for ch in cache.single_char_literals:
        for neighbor in _top_k_syn_neighbors(graph, ch, k):
            if not neighbor or neighbor == ch:
                continue
            for compound in (ch + neighbor, neighbor + ch):
                if len(compound) != 2:
                    continue
                if compound not in cache.two_char_literals:
                    continue
                if compound in base or compound in out:
                    continue
                out.add(compound)
    return out


def build_compound_syn_tiers(
    db: Session,
    *,
    k: int = DEFAULT_SYN_NEIGHBOR_K,
) -> Dict[str, int]:
    """Union 三源候選 → 字面 → tier（curated < morpheme < synthesized）。"""
    cache = ensure_compound_syn_cache(db)
    membership = load_db_char_set(db)
    graph = default_char_relation_graph(db, membership=membership)

    tiers: Dict[str, int] = {}
    for ch in cache.curated_literals:
        tiers[ch] = TIER_CURATED
    for ch in cache.morpheme_literals:
        if ch not in tiers:
            tiers[ch] = TIER_MORPHEME
    for ch in synthesize_compound_literals(cache, graph, k=k):
        if ch not in tiers:
            tiers[ch] = TIER_SYNTHESIZED
    return tiers


__all__ = [
    "DEFAULT_SYN_NEIGHBOR_K",
    "TIER_CURATED",
    "TIER_MORPHEME",
    "TIER_SYNTHESIZED",
    "CompoundSynCache",
    "build_compound_syn_cache",
    "build_compound_syn_tiers",
    "ensure_compound_syn_cache",
    "reset_compound_syn_cache_for_tests",
    "synthesize_compound_literals",
]
