"""Deep module: fetch + merge + rank 近反義關係，供 UI page 與 ~ / ! char 投影共用。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import load_db_char_set
from app.services.syn_ant_ranking import (
    DERIVED_ANT_SOURCES,
    merge_relation_pools,
    morpheme_chars_from_synonyms,
    morpheme_chars_from_word_lists,
    sort_ant_pool,
    sort_syn_pool,
)
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
    from app.services.syn_ant_ranking import final_score

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
    """Per-request ranker: DB relations + static thesaurus + sort → RankedPools."""

    def __init__(self, db: Session, thesaurus: Optional[ThesaurusPort] = None):
        self._db = db
        self._thesaurus = thesaurus or default_thesaurus_port()

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

        q = query.strip()
        from app.services.syn_ant_service import fetch_relations

        db_char_set = load_db_char_set(self._db)

        rel_items: List[dict] = []
        try:
            rel_items = fetch_relations(self._db, q, db_char_set=db_char_set)
        except Exception as exc:
            print(f"[syn] 讀取 word_relations 失敗，將退回 static thesaurus：{exc}")

        static_syns: List[str] = []
        static_ants: List[str] = []
        if include_static:
            static_syns, static_ants = _load_static_pools(q, self._thesaurus)
        morpheme_chars = _resolve_morpheme_chars(q, static_syns, static_ants, self._thesaurus)

        if not quiet:
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
                pool = sort_syn_pool(
                    q, list(merge_relation_pools(db_pool, static_pool).values()), effective_morphemes
                )
            elif relation == "ant":
                effective_morphemes = morpheme_chars if len(q) >= 2 else set()
                pool = sort_ant_pool(
                    q, list(merge_relation_pools(db_pool, static_pool).values()), effective_morphemes
                )
            else:
                pool = db_pool + static_pool
                pool.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))

            for item in pool:
                w = item["char"]
                if not w or w in seen or w == q:
                    continue
                seen.add(w)
                out.append(
                    _syn_result(
                        w,
                        relation,
                        source=item.get("source"),
                        score=item.get("score"),
                        in_db=bool(item.get("in_db")),
                        jyutping=item.get("jyutping") or "",
                        code=item.get("code") or "",
                    )
                )
            return out

        syns = _collect("syn", static_syns)
        ants = _collect("ant", static_ants)

        seen_all = {q} | {r["char"] for r in syns} | {r["char"] for r in ants}
        semantic: List[dict] = []
        for item in [i for i in rel_items if i["relation"] == "semantic_related"]:
            w = item["char"]
            if w and w not in seen_all:
                seen_all.add(w)
                semantic.append(
                    _syn_result(
                        w,
                        "semantic_related",
                        source=item.get("source"),
                        score=item.get("score"),
                        in_db=bool(item.get("in_db")),
                        jyutping=item.get("jyutping") or "",
                        code=item.get("code") or "",
                    )
                )

        return RankedPools(
            query=q,
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
