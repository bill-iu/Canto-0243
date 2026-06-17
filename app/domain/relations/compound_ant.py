"""反義複合（!!）— 快照（源 1、2）與查詢時合成（源 3）。"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, FrozenSet, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.graph import CharRelationGraph, default_char_relation_graph
from app.domain.lexicon.ranking import search_result_sort_key
from app.domain.relations.compound_syn import narrow_compound_syn_literals
from app.lexicon.compound_antonyms import load_compound_antonyms
from app.models.word import Word
from app.repositories.word_relation_repo import load_db_char_set

TIER_CURATED = 0
TIER_MORPHEME = 1
TIER_SYNTHESIZED = 2

DEFAULT_ANT_NEIGHBOR_K = 12

_snapshot: Optional["CompoundAntSnapshot"] = None
_graph: Optional[CharRelationGraph] = None
_tiers_cache: Optional[Dict[str, int]] = None


@dataclass(frozen=True)
class CompoundAntSnapshot:
    """反義複合快照：curated ∩ 詞庫 + 反義素掃描（不含查詢時單字合成）。"""

    curated_literals: FrozenSet[str]
    morpheme_literals: FrozenSet[str]
    two_char_literals: FrozenSet[str]
    single_char_literals: FrozenSet[str]

    @property
    def snapshot_literals(self) -> FrozenSet[str]:
        return self.curated_literals | self.morpheme_literals


def reset_compound_ant_snapshot_for_tests() -> None:
    global _snapshot, _graph, _tiers_cache
    _snapshot = None
    _graph = None
    _tiers_cache = None


def _char_sort_key(ch: str) -> tuple:
    return search_result_sort_key(SimpleNamespace(char=ch, code="", jyutping=""))


def _expand_pair_symmetry(
    compounds: Set[str] | FrozenSet[str],
    two_char_literals: Set[str] | FrozenSet[str],
) -> Set[str]:
    """AB ⇔ BA：僅當反序字面亦在詞庫。"""
    out: Set[str] = set(compounds)
    for ch in compounds:
        if len(ch) != 2:
            continue
        rev = ch[1] + ch[0]
        if rev in two_char_literals:
            out.add(rev)
    return out


def _top_k_ant_neighbors(graph: CharRelationGraph, char: str, k: int) -> list[str]:
    pairs = graph.direct_ant_oriented_pairs()
    neighbors = {b for a, b in pairs if a == char}
    if not neighbors:
        return []
    ordered = sorted(neighbors, key=_char_sort_key)
    return ordered[: max(0, k)]


def _scan_morpheme_ant_compounds(
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
            out.add(compound)
    return out


def build_compound_ant_snapshot(db: Session) -> CompoundAntSnapshot:
    membership = load_db_char_set(db)
    graph = _ensure_relation_graph(db, membership)

    two_char_rows = db.query(Word.char).filter(Word.length == 2).distinct().all()
    two_char_literals = {row[0] for row in two_char_rows if row[0] and len(row[0]) == 2}

    single_rows = db.query(Word.char).filter(Word.length == 1).distinct().all()
    single_char_literals = {row[0] for row in single_rows if row[0] and len(row[0]) == 1}

    curated_raw = {ch for ch in load_compound_antonyms() if ch in two_char_literals and len(ch) == 2}
    curated = _expand_pair_symmetry(curated_raw, two_char_literals)
    morpheme_raw = _scan_morpheme_ant_compounds(graph, two_char_literals)
    morpheme = _expand_pair_symmetry(morpheme_raw, two_char_literals)

    return CompoundAntSnapshot(
        curated_literals=frozenset(curated),
        morpheme_literals=frozenset(ch for ch in morpheme if ch not in curated),
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


def ensure_compound_ant_snapshot(db: Session) -> CompoundAntSnapshot:
    """離線啟動預載：建立反義複合快照（源 1、2）。"""
    global _snapshot
    if _snapshot is None:
        _snapshot = build_compound_ant_snapshot(db)
    return _snapshot


def synthesize_compound_ant_literals(
    snapshot: CompoundAntSnapshot,
    graph: CharRelationGraph,
    *,
    k: int = DEFAULT_ANT_NEIGHBOR_K,
) -> Set[str]:
    """查詢時單字反義合成（源 3）；只回傳詞庫已有 2 字詞。"""
    out: Set[str] = set()
    base = snapshot.snapshot_literals
    for ch in snapshot.single_char_literals:
        for neighbor in _top_k_ant_neighbors(graph, ch, k):
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
    return _expand_pair_symmetry(out, snapshot.two_char_literals)


def _build_compound_ant_tiers_uncached(
    db: Session,
    *,
    k: int = DEFAULT_ANT_NEIGHBOR_K,
) -> Dict[str, int]:
    snapshot = ensure_compound_ant_snapshot(db)
    membership = load_db_char_set(db)
    graph = _ensure_relation_graph(db, membership)

    tiers: Dict[str, int] = {}
    for ch in snapshot.curated_literals:
        tiers[ch] = TIER_CURATED
    for ch in snapshot.morpheme_literals:
        if ch not in tiers:
            tiers[ch] = TIER_MORPHEME
    for ch in synthesize_compound_ant_literals(snapshot, graph, k=k):
        if ch not in tiers:
            tiers[ch] = TIER_SYNTHESIZED
    return tiers


def search_compound_ant(
    db: Session,
    *,
    k: int = DEFAULT_ANT_NEIGHBOR_K,
    rhyme_char: str | None = None,
    width: int = 2,
) -> Dict[str, int]:
    """!! 查詢候選：字面 → tier；可選韻錨縮窄（如 !!你）。"""
    global _tiers_cache
    if _tiers_cache is None:
        _tiers_cache = _build_compound_ant_tiers_uncached(db, k=k)
    tiers = _tiers_cache
    if not rhyme_char or width != 2:
        return tiers
    allowed = narrow_compound_syn_literals(
        frozenset(tiers.keys()), width=width, rhyme_char=rhyme_char, db=db
    )
    return {ch: tiers[ch] for ch in allowed if ch in tiers}


__all__ = [
    "DEFAULT_ANT_NEIGHBOR_K",
    "TIER_CURATED",
    "TIER_MORPHEME",
    "TIER_SYNTHESIZED",
    "CompoundAntSnapshot",
    "build_compound_ant_snapshot",
    "ensure_compound_ant_snapshot",
    "reset_compound_ant_snapshot_for_tests",
    "search_compound_ant",
    "synthesize_compound_ant_literals",
]
