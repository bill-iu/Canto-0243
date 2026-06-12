from __future__ import annotations

import json
from typing import Dict, List, Optional, Set

DERIVED_ANT_SOURCES = frozenset({"ant_syn_mirror", "ant_cilin_exanded"})

QUERY_SYNONYM_PRIORITY: Dict[str, List[str]] = {
    "快樂": ["開心", "愉快", "高興", "歡樂", "快活", "喜悅", "稱快"],
}

QUERY_ANTONYM_PRIORITY: Dict[str, List[str]] = {
    "快樂": ["悲傷", "傷心", "難過", "痛苦", "哀傷", "憂愁", "沮喪"],
}

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


def _source_rank(source: Optional[str]) -> int:
    if not source:
        return 50
    for key, rank in SOURCE_BASE_RANK.items():
        if key in source:
            return rank
    return 40


def final_score(*, source: Optional[str], confidence: Optional[float], in_db: bool) -> float:
    rank = _source_rank(source)
    conf = float(confidence or 0.0)
    bonus = 5.0 if in_db else -10.0
    return rank + conf * 20.0 + bonus


# Back-compat alias
_final_score = final_score


def should_include_synonym(query: str, candidate: str) -> bool:
    if not candidate or candidate == query:
        return False
    if len(query) >= 2 and len(candidate) == 1:
        return False
    return True


_should_include_synonym = should_include_synonym


def merge_relation_pools(db_pool: List[dict], static_pool: List[dict]) -> Dict[str, dict]:
    merged: Dict[str, dict] = {}
    for item in db_pool + static_pool:
        ch = item.get("char") or ""
        if not ch:
            continue
        prev = merged.get(ch)
        if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
            merged[ch] = item
    return merged


_merge_relation_pools = merge_relation_pools


def morpheme_chars_from_word_lists(*word_lists: List[str]) -> Set[str]:
    out: Set[str] = set()
    for words in word_lists:
        out.update(s for s in words if len(s) == 1)
    return out


_morpheme_chars_from_word_lists = morpheme_chars_from_word_lists


def morpheme_chars_from_synonyms(synonyms: List[str]) -> Set[str]:
    return morpheme_chars_from_word_lists(synonyms)


_morpheme_chars_from_synonyms = morpheme_chars_from_synonyms


def _core_compound_boost(query: str, char: str) -> int:
    if len(char) != len(query):
        return 1
    if len(query) >= 2 and char.endswith(("心", "快", "意", "悅")):
        return 0
    return 1


def _core_ant_compound_boost(query: str, char: str) -> int:
    if len(char) != len(query):
        return 1
    if len(query) >= 2 and char.endswith(("傷", "悲", "苦", "痛", "愁", "慘", "過")):
        return 0
    return 1


def parse_group_codes(raw) -> List[str]:
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


_parse_group_codes = parse_group_codes


def _cilin_group_rank(item: dict) -> tuple:
    codes = item.get("_group_codes") or []
    if not codes:
        return (1, "", 0)
    return (0, codes[-1], -len(codes))


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

    key: tuple = (length_tier, preferred)
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


def _syn_relevance_key(query: str, item: dict, morpheme_chars: Optional[Set[str]] = None) -> tuple:
    return _relation_relevance_key(
        query,
        item,
        morpheme_chars,
        preferred_rank_fn=_preferred_synonym_rank,
        core_boost_fn=_core_compound_boost,
        include_group_rank=True,
    )


def _ant_relevance_key(query: str, item: dict, morpheme_chars: Optional[Set[str]] = None) -> tuple:
    return _relation_relevance_key(
        query,
        item,
        morpheme_chars,
        preferred_rank_fn=_preferred_antonym_rank,
        core_boost_fn=_core_ant_compound_boost,
        include_group_rank=False,
    )


def dedupe_rel_items(items: List[dict]) -> List[dict]:
    best: Dict[tuple, dict] = {}
    for item in items:
        key = (item.get("char"), item.get("relation"))
        if not key[0]:
            continue
        prev = best.get(key)
        if prev is None or item.get("_sort", 99) < prev.get("_sort", 99):
            best[key] = item
    return list(best.values())


_dedupe_rel_items = dedupe_rel_items


def sort_syn_pool(query: str, pool: List[dict], morpheme_chars: Optional[Set[str]] = None) -> List[dict]:
    filtered = [i for i in pool if should_include_synonym(query, i.get("char") or "")]
    filtered.sort(key=lambda x: _syn_relevance_key(query, x, morpheme_chars))
    return filtered


_sort_syn_pool = sort_syn_pool


def sort_ant_pool(query: str, pool: List[dict], morpheme_chars: Optional[Set[str]] = None) -> List[dict]:
    filtered = [i for i in pool if should_include_synonym(query, i.get("char") or "")]
    filtered.sort(key=lambda x: _ant_relevance_key(query, x, morpheme_chars))
    return filtered


_sort_ant_pool = sort_ant_pool
