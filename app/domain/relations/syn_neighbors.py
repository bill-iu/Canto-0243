from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.relation_pool_builder import RelationPoolBuilder


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
    syns = RelationPoolBuilder(db).build(opposite, include_static=include_static).chars("syn")
    return {ch for ch in syns if ch and ch not in {seed, opposite}}
