"""Deep module: build ranked 近義 / 反義 / 語意相關 pools (runtime + ingest 同源)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import chars_present_in_db
from app.services.relation_graph import fetch_relation_tuples
from app.services.syn_ant_ranking import (
    dedupe_rel_items,
    final_score,
    merge_relation_pools,
    morpheme_chars_from_synonyms,
    morpheme_chars_from_word_lists,
    normalize_relation_row,
    sort_ant_pool,
    sort_syn_pool,
)
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port


def _load_static_pools(query: str, thesaurus: ThesaurusPort) -> tuple[List[str], List[str]]:
    return thesaurus.get_synonyms(query), thesaurus.get_antonyms(query)


def _resolve_morpheme_chars(
    query: str,
    static_syns: List[str],
    static_ants: List[str],
    thesaurus: ThesaurusPort,
) -> Set[str]:
    if len(query) < 2:
        return set()
    try:
        return morpheme_chars_from_synonyms(thesaurus.get_synonyms(query))
    except Exception:
        pass
    if static_syns:
        return morpheme_chars_from_word_lists(static_syns, static_ants)
    return set()


def _static_relation_pool(relation: str, words: List[str], present: Set[str]) -> List[dict]:
    return [
        {
            "char": w,
            "relation": relation,
            "source": "runtime_static",
            "score": None,
            "in_db": w in present,
            "jyutping": "",
            "code": "",
            "_sort": final_score(source="runtime_static", confidence=0.5, in_db=w in present),
        }
        for w in words
    ]


def _apply_in_db_membership(items: List[dict], present: Set[str]) -> List[dict]:
    out: List[dict] = []
    for item in items:
        ch = item.get("char") or ""
        in_db = ch in present
        patched = dict(item)
        patched["in_db"] = in_db
        patched["_sort"] = final_score(
            source=patched.get("source"),
            confidence=patched.get("score"),
            in_db=in_db,
        )
        out.append(patched)
    return out


def _fetch_db_relations(db: Session, query: str) -> List[dict]:
    q = query.strip()
    if not q:
        return []
    items: List[dict] = []
    for row in fetch_relation_tuples(db, q):
        item = normalize_relation_row(*row, query=q, db_char_set=set())
        if item:
            items.append(item)
    items = dedupe_rel_items(items)
    items.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))
    return items


def _collect_sorted_pool(
    *,
    query: str,
    relation: str,
    rel_items: List[dict],
    static_words: List[str],
    present: Set[str],
    morpheme_chars: Set[str],
) -> List[dict]:
    out: List[dict] = []
    seen: Set[str] = set()
    db_pool = [i for i in rel_items if i["relation"] == relation]
    static_pool = _static_relation_pool(relation, static_words, present)
    if relation == "syn":
        effective_morphemes = morpheme_chars if len(query) >= 2 else set()
        pool = sort_syn_pool(
            query,
            list(merge_relation_pools(db_pool, static_pool).values()),
            effective_morphemes,
        )
    elif relation == "ant":
        effective_morphemes = morpheme_chars if len(query) >= 2 else set()
        pool = sort_ant_pool(
            query,
            list(merge_relation_pools(db_pool, static_pool).values()),
            effective_morphemes,
        )
    else:
        pool = db_pool + static_pool
        pool.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))

    for item in pool:
        ch = item.get("char") or ""
        if not ch or ch in seen or ch == query:
            continue
        seen.add(ch)
        out.append(item)
    return out


@dataclass
class RelationPoolSnapshot:
    """Sorted pool items for one 字面 query."""

    query: str
    syn_pool: List[dict]
    ant_pool: List[dict]
    semantic_pool: List[dict]
    rel_syn: int = 0
    rel_ant: int = 0
    rel_sem: int = 0
    static_syn: int = 0
    static_ant: int = 0

    def chars(self, kind: str) -> List[str]:
        if kind == "syn":
            rows = self.syn_pool
        elif kind == "ant":
            rows = self.ant_pool
        else:
            return []
        return [r["char"] for r in rows if r.get("char")]


class RelationPoolBuilder:
    """Build syn/ant/語意相關 pools — same sources as 近反義模式 / 近義橋反義 ingest."""

    def __init__(
        self,
        db: Session,
        *,
        thesaurus: Optional[ThesaurusPort] = None,
        membership: Optional[Set[str]] = None,
    ) -> None:
        self._db = db
        self._thesaurus = thesaurus or default_thesaurus_port()
        self._membership = membership

    def build(self, query: str, *, include_static: bool = True) -> RelationPoolSnapshot:
        if not query or not re.search(r"[\u4e00-\u9fff]", query):
            return RelationPoolSnapshot(query=query or "", syn_pool=[], ant_pool=[], semantic_pool=[])

        q = query.strip()
        rel_items: List[dict] = []
        try:
            rel_items = _fetch_db_relations(self._db, q)
        except Exception:
            rel_items = []

        static_syns: List[str] = []
        static_ants: List[str] = []
        if include_static:
            static_syns, static_ants = _load_static_pools(q, self._thesaurus)
        morpheme_chars = _resolve_morpheme_chars(q, static_syns, static_ants, self._thesaurus)

        candidate_chars: Set[str] = set()
        for item in rel_items:
            ch = item.get("char")
            if ch:
                candidate_chars.add(ch)
        candidate_chars.update(static_syns)
        candidate_chars.update(static_ants)

        if self._membership is not None:
            present = self._membership
        else:
            present = chars_present_in_db(self._db, candidate_chars)
        rel_items = _apply_in_db_membership(rel_items, present)

        syn_pool = _collect_sorted_pool(
            query=q,
            relation="syn",
            rel_items=rel_items,
            static_words=static_syns,
            present=present,
            morpheme_chars=morpheme_chars,
        )
        ant_pool = _collect_sorted_pool(
            query=q,
            relation="ant",
            rel_items=rel_items,
            static_words=static_ants,
            present=present,
            morpheme_chars=morpheme_chars,
        )

        seen_main = {q} | {r["char"] for r in syn_pool} | {r["char"] for r in ant_pool}
        semantic_pool: List[dict] = []
        for item in rel_items:
            if item.get("relation") != "semantic_related":
                continue
            ch = item.get("char") or ""
            if ch and ch not in seen_main:
                seen_main.add(ch)
                semantic_pool.append(item)

        return RelationPoolSnapshot(
            query=q,
            syn_pool=syn_pool,
            ant_pool=ant_pool,
            semantic_pool=semantic_pool,
            rel_syn=sum(1 for i in rel_items if i["relation"] == "syn"),
            rel_ant=sum(1 for i in rel_items if i["relation"] == "ant"),
            rel_sem=sum(1 for i in rel_items if i["relation"] == "semantic_related"),
            static_syn=len(static_syns),
            static_ant=len(static_ants),
        )


__all__ = [
    "RelationPoolBuilder",
    "RelationPoolSnapshot",
]
