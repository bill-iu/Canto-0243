from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.relation_pool_builder import RelationPoolBuilder


def relation_chars_for_seed(
    db: Session,
    seed_char: str,
    kind: str,
    *,
    include_static: bool = True,
) -> set[str]:
    """近反義池字面投影 — 與 近反義模式 / 近義橋反義 ingest 同源。"""
    if kind not in ("syn", "ant"):
        return set()
    q = (seed_char or "").strip()
    if not q:
        return set()
    return set(
        RelationPoolBuilder(db).build(q, include_static=include_static).chars(kind)
    )
