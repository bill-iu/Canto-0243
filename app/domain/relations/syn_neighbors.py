from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.relations.graph import CharRelationGraph
from app.services.thesaurus_port import default_thesaurus_port


def one_hop_syn_neighbors(
    db: Session,
    *,
    opposite_char: str,
    seed_char: str,
    include_static: bool = True,
) -> set[str]:
    """對端字面的直接近義鄰居（一跳），供創作者手動關係擴展。"""
    opposite = (opposite_char or "").strip()
    seed = (seed_char or "").strip()
    if not opposite:
        return set()
    graph = CharRelationGraph(db, default_thesaurus_port())
    syns = graph.direct_syn_neighbors(opposite, include_static=include_static)
    return {ch for ch in syns if ch and ch not in {seed, opposite}}
