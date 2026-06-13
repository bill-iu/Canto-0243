"""Deep module: fetch + merge + rank 近反義關係，供 UI page 與 ~ / ! char 投影共用。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.services.relation_pool_builder import RelationPoolBuilder
from app.services.syn_ant_ranking import DERIVED_ANT_SOURCES
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port

DEFAULT_PAGE_SIZE = 160


def _syn_result(
    char: str,
    relation: str,
    *,
    source: Optional[str] = None,
    score: Optional[float] = None,
    in_db: bool = False,
    jyutping: str = "",
    code: str = "",
) -> dict:
    return {
        "char": char,
        "code": code,
        "jyutping": jyutping,
        "display_text": char,
        "query_text": char,
        "result_type": "syn",
        "relation": relation,
        "source": source,
        "score": score,
        "in_db": in_db,
    }


def _pool_item_to_result(item: dict, relation: str) -> dict:
    return _syn_result(
        item["char"],
        relation,
        source=item.get("source"),
        score=item.get("score"),
        in_db=bool(item.get("in_db")),
        jyutping=item.get("jyutping") or "",
        code=item.get("code") or "",
    )


def _expand_antonyms_via_syn_endpoints(
    db: Session,
    query: str,
    direct_ants: List[str],
    *,
    include_static: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
) -> List[str]:
    if not direct_ants:
        return []

    port = thesaurus or default_thesaurus_port()
    expanded: List[str] = []
    seen: Set[str] = {query.strip()}

    for ant_char in direct_ants:
        if not ant_char or ant_char in seen:
            continue
        seen.add(ant_char)
        expanded.append(ant_char)

    for ant_char in direct_ants:
        if not ant_char:
            continue
        syn_chars = RelationRanker(db, port).rank(
            ant_char, include_static=include_static
        ).chars("syn", expand=False)
        for syn_char in syn_chars:
            if not syn_char or syn_char in seen:
                continue
            seen.add(syn_char)
            expanded.append(syn_char)

    return expanded


@dataclass
class RankedPools:
    """一次 rank 後的 syn / ant / semantic 池，供 page 與 char 投影。"""

    query: str
    syns: List[dict]
    ants: List[dict]
    semantic: List[dict]
    db: Session
    thesaurus: ThesaurusPort
    include_static: bool

    def page(self, limit: int, offset: int) -> List[dict]:
        if limit < 0:
            limit = DEFAULT_PAGE_SIZE
        if offset < 0:
            offset = 0
        combined = self.syns + self.ants + self.semantic
        return combined[offset : offset + limit]

    def chars(self, kind: str, *, expand: bool = False) -> List[str]:
        if kind not in ("syn", "ant"):
            return []
        rows = self.syns if kind == "syn" else self.ants
        direct = [r["char"] for r in rows if r.get("char")]
        if kind != "ant" or not expand:
            return direct

        q = self.query.strip()
        seed_chars: List[str] = []
        derived_chars: List[str] = []
        seen_seed: Set[str] = set()
        for row in self.ants:
            ch = row.get("char") or ""
            if not ch or ch == q or ch in seen_seed:
                continue
            seen_seed.add(ch)
            src = row.get("source") or ""
            if src in DERIVED_ANT_SOURCES:
                derived_chars.append(ch)
            else:
                seed_chars.append(ch)

        expanded = _expand_antonyms_via_syn_endpoints(
            self.db,
            q,
            seed_chars,
            include_static=self.include_static,
            thesaurus=self.thesaurus,
        )
        if not derived_chars:
            return expanded
        out = list(expanded)
        seen = set(out)
        for ch in derived_chars:
            if ch not in seen:
                seen.add(ch)
                out.append(ch)
        return out


class RelationRanker:
    """Per-request ranker adapter: RelationPoolBuilder → RankedPools (page / expand)."""

    def __init__(self, db: Session, thesaurus: Optional[ThesaurusPort] = None):
        self._db = db
        self._thesaurus = thesaurus or default_thesaurus_port()
        self._builder = RelationPoolBuilder(db, thesaurus=self._thesaurus)

    def rank(self, query: str, *, include_static: bool = True, quiet: bool = False) -> RankedPools:
        if not query or not re.search(r"[\u4e00-\u9fff]", query):
            return RankedPools(
                query=query or "",
                syns=[],
                ants=[],
                semantic=[],
                db=self._db,
                thesaurus=self._thesaurus,
                include_static=include_static,
            )

        snapshot = self._builder.build(query, include_static=include_static)

        if not quiet:
            print(
                f"[syn] q={snapshot.query!r} rel_syn={snapshot.rel_syn} "
                f"rel_ant={snapshot.rel_ant} rel_sem={snapshot.rel_sem} "
                f"static_syn={snapshot.static_syn} static_ant={snapshot.static_ant}"
            )

        syns = [_pool_item_to_result(i, "syn") for i in snapshot.syn_pool]
        ants = [_pool_item_to_result(i, "ant") for i in snapshot.ant_pool]
        semantic = [
            _pool_item_to_result(i, "semantic_related") for i in snapshot.semantic_pool
        ]

        return RankedPools(
            query=snapshot.query,
            syns=syns,
            ants=ants,
            semantic=semantic,
            db=self._db,
            thesaurus=self._thesaurus,
            include_static=include_static,
        )


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "RankedPools",
    "RelationRanker",
]
