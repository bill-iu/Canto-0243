"""詞條列欄位讀取 — domain 層；services.word_serializer re-export 相容。"""

from __future__ import annotations

from app.utils.jyutping_codec import rhyme_finals_from_jyutping
from app.utils.json_helpers import load_json_list


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


def get_rhyme_finals(word) -> list:
    """Rhyme finals from jyutping when available; else stored finals."""
    jp = get_word_jyutping(word)
    if jp:
        derived = rhyme_finals_from_jyutping(jp)
        if derived:
            return derived
    return get_word_parts(word, "finals")


__all__ = [
    "get_rhyme_finals",
    "get_word_jyutping",
    "get_word_parts",
    "get_word_text",
]
