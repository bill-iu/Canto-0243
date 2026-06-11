from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word, WordRelation

DEFAULT_PAGE_SIZE = 160

# High-quality synonyms to surface first for common lyric lookup queries.
QUERY_SYNONYM_PRIORITY: Dict[str, List[str]] = {
    "快樂": ["開心", "愉快", "高興", "歡樂", "快活", "喜悅", "稱快"],
}

# High-quality antonyms to surface first (direct antisem seeds before cilin-expanded).
QUERY_ANTONYM_PRIORITY: Dict[str, List[str]] = {
    "快樂": ["悲傷", "傷心", "難過", "痛苦", "哀傷", "憂愁", "沮喪"],
}


def _preferred_synonym_rank(query: str, char: str) -> int:
    prefs = QUERY_SYNONYM_PRIORITY.get(query, [])
    try:
        return prefs.index(char)
    except ValueError:
        return 999


def _preferred_antonym_rank(query: str, char: str) -> int:
    prefs = QUERY_ANTONYM_PRIORITY.get(query, [])
    try:
        return prefs.index(char)
    except ValueError:
        return 999

SOURCE_BASE_RANK: Dict[str, int] = {
    "manual": 0,
    "cilin": 10,
    "antisem": 10,
    "guotong": 15,
    "ant_cilin_exanded": 25,
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


def _should_include_synonym(query: str, candidate: str) -> bool:
    """For multi-char queries, drop single-character synonym candidates."""
    if not candidate or candidate == query:
        return False
    if len(query) >= 2 and len(candidate) == 1:
        return False
    return True


def _should_include_antonym(query: str, candidate: str) -> bool:
    """Same length/morpheme rules as synonyms for antonym candidates."""
    return _should_include_synonym(query, candidate)


def _morpheme_chars_from_word_lists(*word_lists: List[str]) -> Set[str]:
    """Single-character entries from synonym/antonym lists (Cilin leaf morphemes)."""
    out: Set[str] = set()
    for words in word_lists:
        out.update(s for s in words if len(s) == 1)
    return out


def _morpheme_chars_from_synonyms(synonyms: List[str]) -> Set[str]:
    return _morpheme_chars_from_word_lists(synonyms)


def _core_compound_boost(query: str, char: str) -> int:
    """Prefer standard multi-char compounds (e.g. 開心/愉快) over obscure same-length terms."""
    if len(char) != len(query):
        return 1
    if len(query) >= 2 and char.endswith(("心", "快", "意", "悅")):
        return 0
    return 1


def _core_ant_compound_boost(query: str, char: str) -> int:
    """Prefer standard antonym compounds (e.g. 悲傷/傷心) over obscure same-length terms."""
    if len(char) != len(query):
        return 1
    if len(query) >= 2 and char.endswith(("傷", "悲", "苦", "痛", "愁", "慘", "過")):
        return 0
    return 1


def _parse_group_codes(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(c) for c in raw if c]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(c) for c in parsed if c]
        except (json.JSONDecodeError, TypeError):
            return [raw]
    return []


def _cilin_group_rank(item: dict) -> tuple:
    """Prefer relations with Cilin hierarchy codes; sort by leaf code for stability."""
    codes = item.get("_group_codes") or []
    if not codes:
        return (1, "", 0)
    return (0, codes[-1], -len(codes))


def _syn_relevance_key(query: str, item: dict, morpheme_chars: Optional[Set[str]] = None) -> tuple:
    """Rank synonyms: same length as query first, deprioritize morpheme-prefix compounds."""
    return _relation_relevance_key(
        query,
        item,
        morpheme_chars,
        preferred_rank_fn=_preferred_synonym_rank,
        core_boost_fn=_core_compound_boost,
        include_group_rank=True,
    )


def _ant_relevance_key(query: str, item: dict, morpheme_chars: Optional[Set[str]] = None) -> tuple:
    """Rank antonyms with the same layered relevance as synonyms."""
    return _relation_relevance_key(
        query,
        item,
        morpheme_chars,
        preferred_rank_fn=_preferred_antonym_rank,
        core_boost_fn=_core_ant_compound_boost,
        include_group_rank=False,
    )


def _relation_relevance_key(
    query: str,
    item: dict,
    morpheme_chars: Optional[Set[str]],
    *,
    preferred_rank_fn,
    core_boost_fn,
    include_group_rank: bool,
) -> tuple:
    char = item.get("char") or ""
    q_len = len(query)
    c_len = len(char)
    base_sort = float(item.get("_sort") or 99)
    morpheme_chars = morpheme_chars or set()

    if q_len >= 2 and c_len == 1:
        return (999, 999, 999, 999, 999, char)

    if c_len == q_len:
        length_tier = 0
    elif c_len <= q_len + 2:
        length_tier = 1
    else:
        length_tier = 2

    length_delta = abs(c_len - q_len)
    query_char_overlap = sum(1 for ch in char if ch in query)
    starts_with_morpheme = bool(char and char[0] in morpheme_chars)
    core_boost = core_boost_fn(query, char)
    preferred = preferred_rank_fn(query, char)

    key: tuple = (
        length_tier,
        preferred,
    )
    if include_group_rank:
        has_group, leaf_code, depth = _cilin_group_rank(item)
        key = key + (has_group, leaf_code, depth)
    key = key + (
        core_boost,
        length_delta,
        int(starts_with_morpheme),
        query_char_overlap,
        -base_sort,
        char,
    )
    return key


def _dedupe_rel_items(items: List[dict]) -> List[dict]:
    """Keep best-scored row per (char, relation_type)."""
    best: Dict[tuple, dict] = {}
    for item in items:
        key = (item.get("char"), item.get("relation"))
        if not key[0]:
            continue
        prev = best.get(key)
        if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
            best[key] = item
    return list(best.values())


def _sort_syn_pool(query: str, pool: List[dict], morpheme_chars: Optional[Set[str]] = None) -> List[dict]:
    filtered = [i for i in pool if _should_include_synonym(query, i.get("char") or "")]
    filtered.sort(key=lambda x: _syn_relevance_key(query, x, morpheme_chars))
    return filtered


def _sort_ant_pool(query: str, pool: List[dict], morpheme_chars: Optional[Set[str]] = None) -> List[dict]:
    filtered = [i for i in pool if _should_include_antonym(query, i.get("char") or "")]
    filtered.sort(key=lambda x: _ant_relevance_key(query, x, morpheme_chars))
    return filtered


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
            WordRelation.group_codes,
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
            WordRelation.group_codes,
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
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    include_static: bool = True,
    db_char_set: Optional[Set[str]] = None,
) -> List[dict]:
    """Runtime syn/ant/semantic_related search with bidirectional SQL + static fallback.

    Collects the full ranked result set, then returns ``[offset:offset+limit]`` for pagination.
    """
    if not query or not re.search(r"[\u4e00-\u9fff]", query):
        return []
    q = query.strip()
    if limit < 0:
        limit = DEFAULT_PAGE_SIZE
    if offset < 0:
        offset = 0

    if db_char_set is None:
        db_char_set = {r[0] for r in db.query(Word.char).distinct().all() if r[0]}

    word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]

    rel_items: List[dict] = []
    try:
        for rtype, rchar, source, score, jyutping, code, group_codes_raw in _fetch_relation_rows(db, word_ids):
            if not rchar or rchar == q:
                continue
            in_db = rchar in db_char_set
            group_codes = _parse_group_codes(group_codes_raw)
            rel_items.append({
                "char": rchar,
                "relation": rtype,
                "source": source or "word_relations",
                "score": score,
                "in_db": in_db,
                "jyutping": jyutping or "",
                "code": code or "",
                "group_codes": group_codes,
                "_group_codes": group_codes,
                "_sort": _final_score(source=source, confidence=score, in_db=in_db),
            })
    except Exception as exc:
        print(f"[syn] 讀取 word_relations 失敗，將退回 static thesaurus：{exc}")

    static_syns: List[str] = []
    static_ants: List[str] = []
    morpheme_chars: Set[str] = set()
    if include_static:
        try:
            from utils import get_synonyms, get_antonyms
            static_syns = get_synonyms(q)
            static_ants = get_antonyms(q)
        except Exception:
            pass
    if len(q) >= 2 and not morpheme_chars:
        try:
            from utils import get_synonyms
            morpheme_chars = _morpheme_chars_from_synonyms(get_synonyms(q))
        except Exception:
            pass
    elif len(q) >= 2 and static_syns:
        morpheme_chars = _morpheme_chars_from_word_lists(static_syns, static_ants)

    rel_items = _dedupe_rel_items(rel_items)
    rel_syn = sum(1 for i in rel_items if i["relation"] == "syn")
    rel_ant = sum(1 for i in rel_items if i["relation"] == "ant")
    rel_sem = sum(1 for i in rel_items if i["relation"] == "semantic_related")
    print(
        f"[syn] q={q!r} rel_syn={rel_syn} rel_ant={rel_ant} rel_sem={rel_sem} "
        f"static_syn={len(static_syns)} static_ant={len(static_ants)}"
    )

    rel_items.sort(key=lambda x: (x.get("_sort", 99), x.get("char") or ""))

    def _collect(relation: str, static_words: List[str]) -> List[dict]:
        out: List[dict] = []
        seen: Set[str] = set()
        db_pool = [i for i in rel_items if i["relation"] == relation]
        static_pool = [
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
        if relation == "syn":
            merged: Dict[str, dict] = {}
            for item in db_pool + static_pool:
                ch = item.get("char") or ""
                if not ch:
                    continue
                prev = merged.get(ch)
                if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
                    merged[ch] = item
            effective_morphemes = morpheme_chars if len(q) >= 2 else set()
            pool = _sort_syn_pool(q, list(merged.values()), effective_morphemes)
        elif relation == "ant":
            merged = {}
            for item in db_pool + static_pool:
                ch = item.get("char") or ""
                if not ch:
                    continue
                prev = merged.get(ch)
                if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
                    merged[ch] = item
            effective_morphemes = morpheme_chars if len(q) >= 2 else set()
            pool = _sort_ant_pool(q, list(merged.values()), effective_morphemes)
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


def search_relation_chars(
    db: Session,
    query: str,
    relation_type: str,
    *,
    include_static: bool = True,
) -> List[str]:
    """Return ranked related chars for one relation type (syn or ant)."""
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
    )
    return [r["char"] for r in all_results if r.get("relation") == relation_type and r.get("char")]


def build_char_antonym_pairs(db: Session) -> Set[Tuple[str, str]]:
    """Bidirectional single-char antonym pairs from word_relations + static antisem."""
    from sqlalchemy.orm import aliased

    pairs: Set[Tuple[str, str]] = set()
    w1 = aliased(Word)
    w2 = aliased(Word)
    for a, b in (
        db.query(w1.char, w2.char)
        .join(WordRelation, WordRelation.word_id == w1.id)
        .join(w2, WordRelation.related_id == w2.id)
        .filter(WordRelation.relation_type == "ant")
        .all()
    ):
        if not a or not b or len(a) != 1 or len(b) != 1:
            continue
        pairs.add((a, b))
        pairs.add((b, a))

    try:
        from utils import ensure_thesaurus_loaded
        import utils as u

        ensure_thesaurus_loaded()
        ant_dict = getattr(u, "_ant_dict", {}) or {}
        for ch, ants in ant_dict.items():
            if len(ch) != 1:
                continue
            for ant in ants or []:
                if not ant or len(ant) != 1 or ant == ch:
                    continue
                pairs.add((ch, ant))
                pairs.add((ant, ch))
    except Exception:
        pass

    return pairs
