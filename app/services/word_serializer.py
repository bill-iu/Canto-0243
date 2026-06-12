from __future__ import annotations

from typing import Iterable, List, Optional

from utils import get_0243_code, load_json_list


def deduplicate_words(words: Iterable) -> List:
    seen = set()
    unique = []
    for word in words:
        if isinstance(word, dict):
            c = word.get("char")
        else:
            c = getattr(word, "char", None)
        if c and c not in seen:
            seen.add(c)
            unique.append(word)
    return unique


def paginate(items: List, offset: int, limit: int) -> List:
    if offset < 0:
        offset = 0
    return items[offset : offset + limit]


def serialize_word(
    word,
    *,
    display_text: Optional[str] = None,
    query_text: Optional[str] = None,
    result_type: str = "word",
) -> dict:
    if isinstance(word, dict):
        char_value = word.get("char") or ""
        jyutping_value = word.get("jyutping") or ""
        code_value = word.get("code") or get_0243_code(jyutping_value) or ""
        return {
            "char": char_value,
            "code": code_value or "",
            "jyutping": jyutping_value,
            "display_text": display_text or char_value,
            "query_text": query_text or char_value,
            "result_type": result_type,
            "id": word.get("id"),
        }

    code_value = word.code or get_0243_code(word.jyutping or "") or ""
    return {
        "char": word.char,
        "code": code_value or "",
        "jyutping": word.jyutping or "",
        "display_text": display_text or word.char,
        "query_text": query_text or word.char,
        "result_type": result_type,
        "id": getattr(word, "id", None),
    }


def serialize_page(words: Iterable, offset: int, limit: int, **serialize_kw) -> List[dict]:
    page = paginate(deduplicate_words(words), offset, limit)
    return [serialize_word(w, **serialize_kw) for w in page]


def get_word_text(word) -> str:
    if isinstance(word, dict):
        return word.get("char") or ""
    return getattr(word, "char", "") or ""


def get_word_jyutping(word) -> str:
    if isinstance(word, dict):
        return word.get("jyutping") or ""
    return getattr(word, "jyutping", "") or ""


def get_word_parts(word, field: str) -> list:
    if isinstance(word, dict):
        return word.get(field) or []
    return load_json_list(getattr(word, field, None))


def get_word_sort_code(word) -> str:
    if not word:
        return ""
    if isinstance(word, dict):
        return word.get("code") or get_0243_code(word.get("jyutping") or "") or ""
    return word.code or get_0243_code(word.jyutping or "") or ""


def get_primary_codes(words: Iterable) -> List[str]:
    primary_codes = []
    for word in words:
        code_value = get_word_sort_code(word)
        if code_value and code_value not in primary_codes:
            primary_codes.append(code_value)
    return primary_codes
