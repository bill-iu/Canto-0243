from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word, WordRelation

DEFAULT_CAPS = {"syn": 12, "ant": 8, "semantic_related": 8}

SOURCE_BASE_RANK: Dict[str, int] = {
    "manual": 0,
    "cilin": 10,
    "antisem": 10,
    "guotong": 15,
    "cow": 20,
    "current_static": 15,
    "runtime_static": 80,
    "static_thesaurus": 80,
    "embedding_cosine": 60,
    "word_relations": 50,
}


def _source_rank(source: Optional[str]) -> int:
    if not source:
        return 50
    for key, rank in SOURCE_BASE_RANK.items():
        if key in source:
            return rank
    return 40


def _final_score(
    *,
    source: Optional[str],
    confidence: Optional[float],
    in_db: bool,
) -> float:
    rank = _source_rank(source)
    conf = float(confidence or 0.0)
    bonus = 5.0 if in_db else -10.0
    return rank + conf * 20.0 + bonus


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


def _fetch_relation_rows(db: Session, word_ids: List[int]) -> List[Tuple]:
    """Bidirectional lookup: word_id->related and related->word_id."""
    if not word_ids:
        return []
    forward = (
        db.query(
            WordRelation.relation_type,
            Word.char,
            WordRelation.source,
            WordRelation.score,
            Word.jyutping,
            Word.code,
        )
        .join(Word, WordRelation.related_id == Word.id)
        .filter(WordRelation.word_id.in_(word_ids))
        .filter(WordRelation.relation_type.in_(["syn", "ant", "semantic_related"]))
    )
    backward = (
        db.query(
            WordRelation.relation_type,
            Word.char,
            WordRelation.source,
            WordRelation.score,
            Word.jyutping,
            Word.code,
        )
        .join(Word, WordRelation.word_id == Word.id)
        .filter(WordRelation.related_id.in_(word_ids))
        .filter(WordRelation.relation_type.in_(["syn", "ant", "semantic_related"]))
    )
    return forward.union(backward).all()


def search_syn_ant(
    db: Session,
    query: str,
    *,
    caps: Optional[Dict[str, int]] = None,
    include_static: bool = True,
    db_char_set: Optional[Set[str]] = None,
) -> List[dict]:
    """Runtime syn/ant/semantic_related search with bidirectional SQL + static fallback."""
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return []
    q = query.strip()
    caps = caps or DEFAULT_CAPS

    if db_char_set is None:
        db_char_set = {r[0] for r in db.query(Word.char).distinct().all() if r[0]}

    word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]

    rel_items: List[dict] = []
    try:
        for rtype, rchar, source, score, jyutping, code in _fetch_relation_rows(db, word_ids):
            if not rchar or rchar == q:
                continue
            in_db = rchar in db_char_set
            rel_items.append({
                "char": rchar,
                "relation": rtype,
                "source": source or "word_relations",
                "score": score,
                "in_db": in_db,
                "jyutping": jyutping or "",
                "code": code or "",
                "_sort": _final_score(source=source, confidence=score, in_db=in_db),
            })
    except Exception as exc:
        print(f"[syn] 讀取 word_relations 失敗，將退回 static thesaurus：{exc}")

    static_syns: List[str] = []
    static_ants: List[str] = []
    if include_static:
        try:
            from utils import get_synonyms, get_antonyms
            static_syns = get_synonyms(q)[: caps["syn"]]
            static_ants = get_antonyms(q)[: caps["ant"]]
        except Exception:
            pass

    rel_syn = sum(1 for i in rel_items if i["relation"] == "syn")
    rel_ant = sum(1 for i in rel_items if i["relation"] == "ant")
    rel_sem = sum(1 for i in rel_items if i["relation"] == "semantic_related")
    print(
        f"[syn] q={q!r} rel_syn={rel_syn} rel_ant={rel_ant} rel_sem={rel_sem} "
        f"static_syn={len(static_syns)} static_ant={len(static_ants)}"
    )

    rel_items.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))

    def _collect(relation: str, static_words: List[str], cap: int) -> List[dict]:
        out: List[dict] = []
        seen: Set[str] = set()
        pool = [i for i in rel_items if i["relation"] == relation] + [
            {
                "char": w,
                "relation": relation,
                "source": "runtime_static",
                "score": None,
                "in_db": w in db_char_set,
                "jyutping": "",
                "code": "",
                "_sort": _final_score(source="runtime_static", confidence=0.5, in_db=w in db_char_set),
            }
            for w in static_words
        ]
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
            if len(out) >= cap:
                break
        return out

    syns = _collect("syn", static_syns, caps["syn"])
    ants = _collect("ant", static_ants, caps["ant"])

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
            if len(semantic) >= caps["semantic_related"]:
                break

    return syns + ants + semantic
