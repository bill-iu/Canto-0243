"""查詢時衍生反義 — 詞林衍生反義與反義端點鏡射（CONTEXT § 詞林衍生反義）。"""

from __future__ import annotations

from typing import List, Set

from app.domain.relations.graph import CharRelationGraph
from app.domain.relations.ranking import final_score, sort_ant_pool
from app.domain.thesaurus.port import ThesaurusPort

from app.domain.relations.cilin_derived import (
    CILIN_DERIVED_CONFIDENCE,
    CILIN_DERIVED_SOURCE,
    cilin_derived_ant_pairs,
)
from app.domain.relations.mirror_ant import (
    MIRROR_CONFIDENCE,
    MIRROR_SOURCE,
    mirror_ant_pairs,
)


def _derived_ant_item(
    *,
    char: str,
    source: str,
    confidence: float,
    in_db: bool,
) -> dict:
    return {
        "char": char,
        "relation": "ant",
        "source": source,
        "score": confidence,
        "in_db": in_db,
        "jyutping": "",
        "code": "",
        "_sort": final_score(source=source, confidence=confidence, in_db=in_db),
    }


def runtime_cilin_derived_ant_items(
    query: str,
    seed_chars: List[str],
    *,
    thesaurus: ThesaurusPort,
    present: Set[str],
) -> List[dict]:
    q = query.strip()
    if not q or not seed_chars:
        return []
    thesaurus.ensure_loaded()
    pairs = cilin_derived_ant_pairs(
        q,
        seed_chars,
        cilin_synonyms_of=thesaurus.get_cilin_synonyms,
        membership=present,
    )
    return [
        _derived_ant_item(
            char=tail,
            source=CILIN_DERIVED_SOURCE,
            confidence=CILIN_DERIVED_CONFIDENCE,
            in_db=tail in present,
        )
        for _head, tail in pairs
    ]


def runtime_mirror_ant_items(
    query: str,
    seed_chars: List[str],
    *,
    graph: CharRelationGraph,
    present: Set[str],
    include_static: bool,
) -> List[dict]:
    q = query.strip()
    if not q or not seed_chars:
        return []
    pairs = mirror_ant_pairs(
        q,
        seed_chars,
        syn_neighbors_of=lambda s: graph.direct_syn_neighbors(
            s, include_static=include_static
        ),
        membership=present,
    )
    return [
        _derived_ant_item(
            char=tail,
            source=MIRROR_SOURCE,
            confidence=MIRROR_CONFIDENCE,
            in_db=tail in present,
        )
        for _head, tail in pairs
    ]


def append_runtime_derived_ant_pool(
    query: str,
    ant_pool: List[dict],
    *,
    thesaurus: ThesaurusPort,
    graph: CharRelationGraph,
    present: Set[str],
    include_static: bool,
    morpheme_chars: Set[str],
) -> List[dict]:
    seeds = [item.get("char") or "" for item in ant_pool if item.get("char")]
    cilin_items = runtime_cilin_derived_ant_items(
        query, seeds, thesaurus=thesaurus, present=present
    )
    merged = {item["char"]: item for item in ant_pool}
    for item in cilin_items:
        prev = merged.get(item["char"])
        if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
            merged[item["char"]] = item
    mirror_items = runtime_mirror_ant_items(
        query,
        seeds,
        graph=graph,
        present=present,
        include_static=include_static,
    )
    for item in mirror_items:
        prev = merged.get(item["char"])
        if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
            merged[item["char"]] = item
    return sort_ant_pool(query, list(merged.values()), morpheme_chars)


__all__ = [
    "CILIN_DERIVED_CONFIDENCE",
    "CILIN_DERIVED_SOURCE",
    "MIRROR_CONFIDENCE",
    "MIRROR_SOURCE",
    "append_runtime_derived_ant_pool",
    "runtime_cilin_derived_ant_items",
    "runtime_mirror_ant_items",
]
