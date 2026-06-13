"""近反義池對外搜尋入口（供 router / 測試）。"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.pool import DEFAULT_PAGE_SIZE, build_pool
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port


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
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return []
    snapshot = build_pool(
        db,
        query.strip(),
        include_static=include_static,
        thesaurus=thesaurus or default_thesaurus_port(),
        membership=db_char_set,
        quiet=True,
    )
    return snapshot.page(limit, offset)


def search_relation_chars(
    db: Session,
    query: str,
    relation_type: str,
    *,
    include_static: bool = True,
    expand_ant_via_syn: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
) -> List[str]:
    if relation_type not in ("syn", "ant"):
        return []
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return []
    snapshot = build_pool(
        db,
        query.strip(),
        include_static=include_static,
        thesaurus=thesaurus or default_thesaurus_port(),
        quiet=True,
    )
    expand = relation_type == "ant" and expand_ant_via_syn
    return snapshot.chars(relation_type, expand=expand)


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "search_syn_ant",
    "search_relation_chars",
]
