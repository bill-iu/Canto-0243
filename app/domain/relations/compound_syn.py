"""近義複合（~~）— 快照（源 1、2）與查詢時合成（源 3）。"""

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

_snapshot: Optional["CompoundSynSnapshot"] = None
_graph: Optional[CharRelationGraph] = None
_tiers_cache: Optional[Dict[str, int]] = None


@dataclass(frozen=True)
class CompoundSynSnapshot:
    """近義複合快照：curated ∩ 詞庫 + 同義素掃描（不含查詢時單字合成）。"""

    curated_literals: FrozenSet[str]
    morpheme_literals: FrozenSet[str]
    two_char_literals: FrozenSet[str]
    single_char_literals: FrozenSet[str]

    @property
    def snapshot_literals(self) -> FrozenSet[str]:
        return self.curated_literals | self.morpheme_literals


def reset_compound_syn_snapshot_for_tests() -> None:
    global _snapshot, _graph, _tiers_cache
    _snapshot = None
    _graph = None
    _tiers_cache = None


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


def build_compound_syn_snapshot(db: Session) -> CompoundSynSnapshot:
    membership = load_db_char_set(db)
    graph = _ensure_relation_graph(db, membership)

    two_char_rows = db.query(Word.char).filter(Word.length == 2).distinct().all()
    two_char_literals = {row[0] for row in two_char_rows if row[0] and len(row[0]) == 2}

    single_rows = db.query(Word.char).filter(Word.length == 1).distinct().all()
    single_char_literals = {row[0] for row in single_rows if row[0] and len(row[0]) == 1}

    curated_file = [ch for ch in load_compound_synonyms() if ch in two_char_literals]
    morpheme = _scan_morpheme_compounds(db, graph, two_char_literals)

    return CompoundSynSnapshot(
        curated_literals=frozenset(curated_file),
        morpheme_literals=frozenset(morpheme),
        two_char_literals=frozenset(two_char_literals),
        single_char_literals=frozenset(single_char_literals),
    )


def _ensure_relation_graph(db: Session, membership: set[str] | None = None) -> CharRelationGraph:
    global _graph
    if _graph is None:
        if membership is None:
            membership = load_db_char_set(db)
        _graph = default_char_relation_graph(db, membership=membership)
    return _graph


def ensure_compound_syn_snapshot(db: Session) -> CompoundSynSnapshot:
    """離線啟動預載：建立近義複合快照（源 1、2）。"""
    global _snapshot
    if _snapshot is None:
        _snapshot = build_compound_syn_snapshot(db)
    return _snapshot


def synthesize_compound_literals(
    snapshot: CompoundSynSnapshot,
    graph: CharRelationGraph,
    *,
    k: int = DEFAULT_SYN_NEIGHBOR_K,
) -> Set[str]:
    """查詢時單字近義合成（源 3）；只回傳詞庫已有 2 字詞。"""
    out: Set[str] = set()
    base = snapshot.snapshot_literals
    for ch in snapshot.single_char_literals:
        for neighbor in _top_k_syn_neighbors(graph, ch, k):
            if not neighbor or neighbor == ch:
                continue
            for compound in (ch + neighbor, neighbor + ch):
                if len(compound) != 2:
                    continue
                if compound not in snapshot.two_char_literals:
                    continue
                if compound in base or compound in out:
                    continue
                out.add(compound)
    return out


def _build_compound_syn_tiers_uncached(
    db: Session,
    *,
    k: int = DEFAULT_SYN_NEIGHBOR_K,
) -> Dict[str, int]:
    snapshot = ensure_compound_syn_snapshot(db)
    membership = load_db_char_set(db)
    graph = _ensure_relation_graph(db, membership)

    tiers: Dict[str, int] = {}
    for ch in snapshot.curated_literals:
        tiers[ch] = TIER_CURATED
    for ch in snapshot.morpheme_literals:
        if ch not in tiers:
            tiers[ch] = TIER_MORPHEME
    for ch in synthesize_compound_literals(snapshot, graph, k=k):
        if ch not in tiers:
            tiers[ch] = TIER_SYNTHESIZED
    return tiers


def search_compound_syn(
    db: Session,
    *,
    k: int = DEFAULT_SYN_NEIGHBOR_K,
) -> Dict[str, int]:
    """~~ 查詢候選：快照 union 查詢時單字近義合成，回傳字面 → tier。"""
    global _tiers_cache
    if _tiers_cache is not None:
        return _tiers_cache
    _tiers_cache = _build_compound_syn_tiers_uncached(db, k=k)
    return _tiers_cache


def narrow_compound_syn_literals(
    literals: FrozenSet[str] | set[str],
    *,
    width: int,
    rhyme_char: str | None,
    db: Session,
) -> frozenset[str]:
    """韻／聲錨查詢前縮小候選字面（如 ~~港）。"""
    if not rhyme_char or width != 2:
        return frozenset(literals)
    from app.utils.word_cache_index import get_phoneme_index_candidates
    from app.services.word_serializer import get_word_text

    phoneme_rows = get_phoneme_index_candidates(width, width - 1, rhyme_char, "final", db)
    if phoneme_rows:
        allowed = {get_word_text(w) for w in phoneme_rows}
        return frozenset(ch for ch in literals if ch in allowed)
    return frozenset(literals)


__all__ = [
    "DEFAULT_SYN_NEIGHBOR_K",
    "TIER_CURATED",
    "TIER_MORPHEME",
    "TIER_SYNTHESIZED",
    "CompoundSynSnapshot",
    "build_compound_syn_snapshot",
    "ensure_compound_syn_snapshot",
    "reset_compound_syn_snapshot_for_tests",
    "search_compound_syn",
    "synthesize_compound_literals",
    "narrow_compound_syn_literals",
]
