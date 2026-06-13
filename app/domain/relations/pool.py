"""近反義池 — build_pool + PoolSnapshot（runtime + ingest 同源）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.graph import CharRelationGraph
from app.domain.relations.ranking import (
    DERIVED_ANT_SOURCES,
    dedupe_rel_items,
    final_score,
    merge_relation_pools,
    morpheme_chars_from_synonyms,
    morpheme_chars_from_word_lists,
    normalize_relation_row,
    sort_ant_pool,
    sort_syn_pool,
)
from app.models.word import Word
from app.repositories.word_relation_repo import chars_present_in_db, fetch_bidirectional_relations
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port

DEFAULT_PAGE_SIZE = 160


def _fetch_relation_tuples(db: Session, query: str) -> List[tuple]:
    q = query.strip()
    if not q:
        return []
    word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]
    return fetch_bidirectional_relations(db, word_ids)


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
    for row in _fetch_relation_tuples(db, q):
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


def _ui_result(item: dict, relation: str) -> dict:
    char = item["char"]
    return {
        "char": char,
        "code": item.get("code") or "",
        "jyutping": item.get("jyutping") or "",
        "display_text": char,
        "query_text": char,
        "result_type": "syn",
        "relation": relation,
        "source": item.get("source"),
        "score": item.get("score"),
        "in_db": bool(item.get("in_db")),
    }


def _expand_ant_chars_via_graph(
    graph: CharRelationGraph,
    query: str,
    seed_chars: List[str],
) -> List[str]:
    if not seed_chars:
        return []
    q = query.strip()
    expanded: List[str] = []
    seen: Set[str] = {q}
    for ant_char in seed_chars:
        if ant_char and ant_char not in seen:
            seen.add(ant_char)
            expanded.append(ant_char)
        for syn_char in graph.direct_syn_neighbors(ant_char):
            if syn_char and syn_char not in seen:
                seen.add(syn_char)
                expanded.append(syn_char)
    return expanded


@dataclass
class PoolSnapshot:
    """近反義池快照：供近反義模式 page 與 ~ / ! char 投影。"""

    query: str
    syns: List[dict]
    ants: List[dict]
    semantic: List[dict]
    rel_syn: int = 0
    rel_ant: int = 0
    rel_sem: int = 0
    static_syn: int = 0
    static_ant: int = 0
    _db: Session = None  # type: ignore[assignment]
    _thesaurus: Optional[ThesaurusPort] = None
    _include_static: bool = True
    _membership: Optional[Set[str]] = None

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

        graph = CharRelationGraph(
            self._db,
            self._thesaurus or default_thesaurus_port(),
            membership=self._membership,
        )
        expanded = _expand_ant_chars_via_graph(graph, q, seed_chars)
        if not derived_chars:
            return expanded
        out = list(expanded)
        seen = set(out)
        for ch in derived_chars:
            if ch not in seen:
                seen.add(ch)
                out.append(ch)
        return out


def build_pool(
    db: Session,
    query: str,
    *,
    include_static: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
    quiet: bool = False,
) -> PoolSnapshot:
    port = thesaurus or default_thesaurus_port()
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return PoolSnapshot(
            query=query or "",
            syns=[],
            ants=[],
            semantic=[],
            _db=db,
            _thesaurus=port,
            _include_static=include_static,
            _membership=membership,
        )

    q = query.strip()
    rel_items: List[dict] = []
    try:
        rel_items = _fetch_db_relations(db, q)
    except Exception:
        rel_items = []

    static_syns: List[str] = []
    static_ants: List[str] = []
    if include_static:
        static_syns, static_ants = _load_static_pools(q, port)
    morpheme_chars = _resolve_morpheme_chars(q, static_syns, static_ants, port)

    candidate_chars: Set[str] = set()
    for item in rel_items:
        ch = item.get("char")
        if ch:
            candidate_chars.add(ch)
    candidate_chars.update(static_syns)
    candidate_chars.update(static_ants)

    if membership is not None:
        present = membership
    else:
        present = chars_present_in_db(db, candidate_chars)
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

    if not quiet:
        print(
            f"[syn] q={q!r} rel_syn={sum(1 for i in rel_items if i['relation'] == 'syn')} "
            f"rel_ant={sum(1 for i in rel_items if i['relation'] == 'ant')} "
            f"rel_sem={sum(1 for i in rel_items if i['relation'] == 'semantic_related')} "
            f"static_syn={len(static_syns)} static_ant={len(static_ants)}"
        )

    return PoolSnapshot(
        query=q,
        syns=[_ui_result(i, "syn") for i in syn_pool],
        ants=[_ui_result(i, "ant") for i in ant_pool],
        semantic=[_ui_result(i, "semantic_related") for i in semantic_pool],
        rel_syn=sum(1 for i in rel_items if i["relation"] == "syn"),
        rel_ant=sum(1 for i in rel_items if i["relation"] == "ant"),
        rel_sem=sum(1 for i in rel_items if i["relation"] == "semantic_related"),
        static_syn=len(static_syns),
        static_ant=len(static_ants),
        _db=db,
        _thesaurus=port,
        _include_static=include_static,
        _membership=membership,
    )


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "PoolSnapshot",
    "build_pool",
]
