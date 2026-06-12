from __future__ import annotations

import re
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import load_db_char_set
from app.services.char_antonym_pairs import build_char_antonym_pairs  # re-exported
from app.services.relation_graph import fetch_relation_tuples
from app.services.syn_ant_ranking import (
    DERIVED_ANT_SOURCES,
    dedupe_rel_items,
    final_score,
    merge_relation_pools,
    morpheme_chars_from_synonyms,
    morpheme_chars_from_word_lists,
    parse_group_codes,
    sort_ant_pool,
    sort_syn_pool,
)
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port

DEFAULT_PAGE_SIZE = 160

from app.services.syn_ant_ranking import (  # noqa: E402
    final_score as _final_score,
    sort_ant_pool as _sort_ant_pool,
    sort_syn_pool as _sort_syn_pool,
    should_include_synonym as _should_include_synonym,
)


def normalize_relation_row(
    rtype: str,
    rchar: str,
    source,
    score,
    jyutping,
    code,
    group_codes_raw,
    *,
    query: str,
    db_char_set: Set[str],
) -> dict | None:
    if not rchar or rchar == query:
        return None
    in_db = rchar in db_char_set
    group_codes = parse_group_codes(group_codes_raw)
    return {
        "char": rchar,
        "relation": rtype,
        "source": source or "word_relations",
        "score": score,
        "in_db": in_db,
        "jyutping": jyutping or "",
        "code": code or "",
        "group_codes": group_codes,
        "_group_codes": group_codes,
        "_sort": final_score(source=source, confidence=score, in_db=in_db),
    }


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


def _static_relation_pool(relation: str, words: List[str], db_char_set: Set[str]) -> List[dict]:
    return [
        {
            "char": w,
            "relation": relation,
            "source": "runtime_static",
            "score": None,
            "in_db": w in db_char_set,
            "jyutping": "",
            "code": "",
            "_sort": final_score(source="runtime_static", confidence=0.5, in_db=w in db_char_set),
        }
        for w in words
    ]


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
    q = query.strip()
    if limit < 0:
        limit = DEFAULT_PAGE_SIZE
    if offset < 0:
        offset = 0

    port = thesaurus or default_thesaurus_port()

    if db_char_set is None:
        db_char_set = load_db_char_set(db)

    rel_items: List[dict] = []
    try:
        rel_items = fetch_relations(db, q, db_char_set=db_char_set)
    except Exception as exc:
        print(f"[syn] 讀取 word_relations 失敗，將退回 static thesaurus：{exc}")

    static_syns: List[str] = []
    static_ants: List[str] = []
    if include_static:
        static_syns, static_ants = _load_static_pools(q, port)
    morpheme_chars = _resolve_morpheme_chars(q, static_syns, static_ants, port)

    rel_syn = sum(1 for i in rel_items if i["relation"] == "syn")
    rel_ant = sum(1 for i in rel_items if i["relation"] == "ant")
    rel_sem = sum(1 for i in rel_items if i["relation"] == "semantic_related")
    print(
        f"[syn] q={q!r} rel_syn={rel_syn} rel_ant={rel_ant} rel_sem={rel_sem} "
        f"static_syn={len(static_syns)} static_ant={len(static_ants)}"
    )

    def _collect(relation: str, static_words: List[str]) -> List[dict]:
        out: List[dict] = []
        seen: Set[str] = set()
        db_pool = [i for i in rel_items if i["relation"] == relation]
        static_pool = _static_relation_pool(relation, static_words, db_char_set)
        if relation == "syn":
            effective_morphemes = morpheme_chars if len(q) >= 2 else set()
            pool = sort_syn_pool(q, list(merge_relation_pools(db_pool, static_pool).values()), effective_morphemes)
        elif relation == "ant":
            effective_morphemes = morpheme_chars if len(q) >= 2 else set()
            pool = sort_ant_pool(q, list(merge_relation_pools(db_pool, static_pool).values()), effective_morphemes)
        else:
            pool = db_pool + static_pool
            pool.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))

        for item in pool:
            w = item["char"]
            if not w or w in seen or w == q:
                continue
            seen.add(w)
            out.append(_syn_result(
                w,
                relation,
                source=item.get("source"),
                score=item.get("score"),
                in_db=bool(item.get("in_db")),
                jyutping=item.get("jyutping") or "",
                code=item.get("code") or "",
            ))
        return out

    syns = _collect("syn", static_syns)
    ants = _collect("ant", static_ants)

    seen_all = {q} | {r["char"] for r in syns} | {r["char"] for r in ants}
    semantic: List[dict] = []
    for item in [i for i in rel_items if i["relation"] == "semantic_related"]:
        w = item["char"]
        if w and w not in seen_all:
            seen_all.add(w)
            semantic.append(_syn_result(
                w,
                "semantic_related",
                source=item.get("source"),
                score=item.get("score"),
                in_db=bool(item.get("in_db")),
                jyutping=item.get("jyutping") or "",
                code=item.get("code") or "",
            ))

    combined = syns + ants + semantic
    return combined[offset : offset + limit]


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
        syn_chars = search_relation_chars(
            db,
            ant_char,
            "syn",
            include_static=include_static,
            thesaurus=thesaurus,
        )
        for syn_char in syn_chars:
            if not syn_char or syn_char in seen:
                continue
            seen.add(syn_char)
            expanded.append(syn_char)

    return expanded


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
    q = query.strip()
    all_results = search_syn_ant(
        db,
        q,
        limit=10**9,
        offset=0,
        include_static=include_static,
        thesaurus=thesaurus,
    )
    direct = [r["char"] for r in all_results if r.get("relation") == relation_type and r.get("char")]
    if relation_type == "ant" and expand_ant_via_syn:
        seed_chars: List[str] = []
        derived_chars: List[str] = []
        seen_seed: Set[str] = set()
        for r in all_results:
            if r.get("relation") != "ant":
                continue
            ch = r.get("char") or ""
            if not ch or ch == q or ch in seen_seed:
                continue
            seen_seed.add(ch)
            src = r.get("source") or ""
            if src in DERIVED_ANT_SOURCES:
                derived_chars.append(ch)
            else:
                seed_chars.append(ch)

        expanded = _expand_antonyms_via_syn_endpoints(
            db,
            q,
            seed_chars,
            include_static=include_static,
            thesaurus=thesaurus,
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
    return direct


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
