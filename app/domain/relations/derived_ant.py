"""查詢時衍生反義 — 詞林衍生反義與反義端點鏡射（CONTEXT § 詞林衍生反義）。"""

from __future__ import annotations

from typing import List, Optional, Set

from app.domain.relations.graph import CharRelationGraph
from app.domain.relations.ranking import final_score, sort_ant_pool
from app.domain.relations.valid_term import normalize_literal
from app.domain.thesaurus.port import ThesaurusPort

CILIN_DERIVED_SOURCE = "ant_cilin_exanded"
MIRROR_SOURCE = "ant_syn_mirror"
CILIN_DERIVED_CONFIDENCE = 0.75
MIRROR_CONFIDENCE = 0.72


def _pool_literal(text: str) -> Optional[str]:
    return normalize_literal(text)


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
    out: List[dict] = []
    seen: Set[str] = {q}
    for seed in seed_chars:
        seed = (seed or "").strip()
        if not seed:
            continue
        thesaurus.ensure_loaded()
        for syn in thesaurus.get_cilin_synonyms(seed):
            ch = _pool_literal(syn)
            if not ch or ch == q or ch in seen or ch not in present:
                continue
            seen.add(ch)
            in_db = ch in present
            out.append(
                _derived_ant_item(
                    char=ch,
                    source=CILIN_DERIVED_SOURCE,
                    confidence=CILIN_DERIVED_CONFIDENCE,
                    in_db=in_db,
                )
            )
    return out


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
    out: List[dict] = []
    seen: Set[str] = {q}
    for seed in seed_chars:
        seed = (seed or "").strip()
        if not seed or seed in seen:
            continue
        seen.add(seed)
        for syn in graph.direct_syn_neighbors(seed, include_static=include_static):
            ch = _pool_literal(syn)
            if not ch or ch == q or ch in seen or ch not in present:
                continue
            seen.add(ch)
            in_db = ch in present
            out.append(
                _derived_ant_item(
                    char=ch,
                    source=MIRROR_SOURCE,
                    confidence=MIRROR_CONFIDENCE,
                    in_db=in_db,
                )
            )
    return out


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
