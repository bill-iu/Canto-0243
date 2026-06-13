from __future__ import annotations

import re
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import load_db_char_set
from app.services.char_antonym_pairs import build_char_antonym_pairs  # re-exported
from app.services.relation_graph import fetch_relation_tuples
from app.services.relation_ranker import DEFAULT_PAGE_SIZE, RelationRanker
from app.services.syn_ant_ranking import (
    dedupe_rel_items,
    normalize_relation_row,
)
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port

from app.services.syn_ant_ranking import (  # noqa: E402
    final_score as _final_score,
    sort_ant_pool as _sort_ant_pool,
    sort_syn_pool as _sort_syn_pool,
    should_include_synonym as _should_include_synonym,
)



def fetch_relations(
    db: Session,
    query: str,
    kind: Optional[str] = None,
    *,
    db_char_set: Optional[Set[str]] = None,
) -> List[dict]:
    """Single entry: DB relations for *query*, optionally filtered by *kind*, ranked."""
    q = query.strip()
    if not q:
        return []
    if db_char_set is None:
        db_char_set = load_db_char_set(db)

    items: List[dict] = []
    for row in fetch_relation_tuples(db, q):
        item = normalize_relation_row(*row, query=q, db_char_set=db_char_set)
        if item:
            items.append(item)

    items = dedupe_rel_items(items)
    items.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))
    if kind:
        items = [i for i in items if i["relation"] == kind]
    return items


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
    port = thesaurus or default_thesaurus_port()
    pools = RelationRanker(db, port).rank(query.strip(), include_static=include_static)
    return pools.page(limit, offset)


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
    port = thesaurus or default_thesaurus_port()
    pools = RelationRanker(db, port).rank(query.strip(), include_static=include_static)
    expand = relation_type == "ant" and expand_ant_via_syn
    return pools.chars(relation_type, expand=expand)


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "build_char_antonym_pairs",
    "fetch_relations",
    "normalize_relation_row",
    "search_syn_ant",
    "search_relation_chars",
    "_final_score",
    "_sort_syn_pool",
    "_sort_ant_pool",
    "_should_include_synonym",
]
