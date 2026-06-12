from __future__ import annotations

from typing import List, Set, Tuple

from utils import get_antonyms, get_synonyms

from app.services.syn_ant_ranking import final_score, morpheme_chars_from_synonyms, morpheme_chars_from_word_lists


def load_static_pools(query: str) -> tuple[List[str], List[str]]:
    try:
        return get_synonyms(query), get_antonyms(query)
    except Exception:
        return [], []


def resolve_morpheme_chars(query: str, static_syns: List[str], static_ants: List[str]) -> Set[str]:
    if len(query) < 2:
        return set()
    try:
        return morpheme_chars_from_synonyms(get_synonyms(query))
    except Exception:
        pass
    if static_syns:
        return morpheme_chars_from_word_lists(static_syns, static_ants)
    return set()


def static_relation_pool(relation: str, words: List[str], db_char_set: Set[str]) -> List[dict]:
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


def fetch_static_char_ant_pairs() -> Set[Tuple[str, str]]:
    from app.thesaurus.static_index import iter_antonym_edges
    from utils import ensure_thesaurus_loaded

    pairs: Set[Tuple[str, str]] = set()
    try:
        ensure_thesaurus_loaded()
        for ch, ant in iter_antonym_edges():
            if len(ch) != 1 or not ant or len(ant) != 1 or ant == ch:
                continue
            pairs.add((ch, ant))
            pairs.add((ant, ch))
    except Exception:
        pass
    return pairs
