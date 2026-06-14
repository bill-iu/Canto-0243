"""近反義池對外搜尋入口（供 router / 測試）。"""

from __future__ import annotations

from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.pool import DEFAULT_PAGE_SIZE
from app.domain.relations.pool_projection import relation_pool_chars, relation_pool_page
from app.domain.thesaurus.port import ThesaurusPort


def search_syn_ant(
    db: Session,
    query: str,
    *,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    include_static: bool = True,
    db_char_set: Optional[Set[str]] = None,
    thesaurus: Optional[ThesaurusPort] = None,
) -> List[dict]:
    return relation_pool_page(
        db,
        query,
        limit=limit,
        offset=offset,
        include_static=include_static,
        thesaurus=thesaurus,
        membership=db_char_set,
    )


def search_relation_chars(
    db: Session,
    query: str,
    relation_type: str,
    *,
    include_static: bool = True,
    expand_ant_via_syn: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
) -> List[str]:
    return relation_pool_chars(
        db,
        query,
        relation_type,
        include_static=include_static,
        expand_ant_via_syn=expand_ant_via_syn,
        thesaurus=thesaurus,
    )


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "search_syn_ant",
    "search_relation_chars",
]
