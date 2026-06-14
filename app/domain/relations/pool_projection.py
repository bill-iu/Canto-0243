"""Runtime 近反義池投影 — CONTEXT § 近反義池（讀取收口）。"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.pool import DEFAULT_PAGE_SIZE, PoolSnapshot, build_pool
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port


def project_relation_pool(
    db: Session,
    seed_char: str,
    *,
    include_static: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
) -> PoolSnapshot:
    """Runtime 近反義池投影：統一 build_pool 讀取入口（規則不變）。"""
    return build_pool(
        db,
        seed_char,
        include_static=include_static,
        thesaurus=thesaurus or default_thesaurus_port(),
        membership=membership,
        quiet=True,
    )


def relation_pool_page(
    db: Session,
    seed_char: str,
    *,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    include_static: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
) -> List[dict]:
    if not seed_char or not re.search(r"[\u4e00-\u9fff]", seed_char):
        return []
    return project_relation_pool(
        db,
        seed_char.strip(),
        include_static=include_static,
        thesaurus=thesaurus,
        membership=membership,
    ).page(limit, offset)


def relation_pool_chars(
    db: Session,
    seed_char: str,
    relation_type: str,
    *,
    include_static: bool = True,
    expand_ant_via_syn: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
) -> List[str]:
    if relation_type not in ("syn", "ant"):
        return []
    if not seed_char or not re.search(r"[\u4e00-\u9fff]", seed_char):
        return []
    snapshot = project_relation_pool(
        db,
        seed_char.strip(),
        include_static=include_static,
        thesaurus=thesaurus,
    )
    expand = relation_type == "ant" and expand_ant_via_syn
    return snapshot.chars(relation_type, expand=expand)


def relation_chars_for_seed(
    db: Session,
    seed_char: str,
    kind: str,
    *,
    include_static: bool = True,
) -> set[str]:
    """種子字面在指定關係類型上的池字面集合（擴展互斥等用途）。"""
    if kind not in ("syn", "ant"):
        return set()
    q = (seed_char or "").strip()
    if not q:
        return set()
    return set(
        project_relation_pool(db, q, include_static=include_static).chars(kind)
    )


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "PoolSnapshot",
    "project_relation_pool",
    "relation_chars_for_seed",
    "relation_pool_chars",
    "relation_pool_page",
]
