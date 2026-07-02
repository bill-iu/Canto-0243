"""近反義池建構 — build_pool 實作（由 pool_projection 或測試呼叫；新碼優先投影）。"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.domain.relations.derived_ant import append_runtime_derived_ant_pool
from app.domain.relations.graph import get_process_cached_graph
from app.domain.relations.pool import DEFAULT_PAGE_SIZE, PoolSnapshot
from app.domain.relations.ranking import (
    RUNTIME_DERIVED_ANT_SOURCES,
    dedupe_rel_items,
    final_score,
    merge_relation_pools,
    morpheme_chars_from_synonyms,
    morpheme_chars_from_word_lists,
    normalize_relation_row,
    sort_ant_pool,
    sort_syn_pool,
)
from app.domain.relations.valid_term import normalize_literal
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.models.word import Word
from app.repositories.word_relation_repo import (
    chars_present_in_db,
    fetch_bidirectional_relations,
    load_db_char_set,
)


def _pool_literal(text: str) -> Optional[str]:
    return normalize_literal(text)


def _filter_static_words(words: List[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for w in words:
        t = _pool_literal(w)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _filter_pool_items(items: List[dict]) -> List[dict]:
    out: List[dict] = []
    for item in items:
        ch = _pool_literal(item.get("char") or "")
        if not ch:
            continue
        patched = dict(item)
        patched["char"] = ch
        out.append(patched)
    return out


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
    words = _filter_static_words(words)
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
    items = [
        item
        for item in items
        if (item.get("source") or "") not in RUNTIME_DERIVED_ANT_SOURCES
    ]
    items.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))
    return _filter_pool_items(items)


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


def build_pool(
    db: Session,
    query: str,
    *,
    include_static: bool = True,
    include_derived_ant: bool = True,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
    quiet: bool = False,
) -> PoolSnapshot:
    """建構近反義池快照。新 runtime 路徑應經 pool_projection.project_relation_pool。"""
    port = thesaurus or default_thesaurus_port()
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return PoolSnapshot(
            query=query or "",
            syns=[],
            ants=[],
            semantic=[],
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
        static_syns = _filter_static_words(static_syns)
        static_ants = _filter_static_words(static_ants)
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
        lexicon_membership = membership
    else:
        present = chars_present_in_db(db, candidate_chars)
        lexicon_membership = load_db_char_set(db)
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
    if include_derived_ant:
        graph = get_process_cached_graph(
            db,
            port,
            membership=lexicon_membership,
        )
        ant_pool = append_runtime_derived_ant_pool(
            q,
            ant_pool,
            db=db,
            thesaurus=port,
            graph=graph,
            present=lexicon_membership,
            include_static=include_static,
            morpheme_chars=morpheme_chars,
            head_syns={r.get("char") or "" for r in syn_pool if r.get("char")},
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
    )


__all__ = ["build_pool"]
