"""詞條列欄位讀取 — domain 層；services.word_serializer re-export 相容。"""

from __future__ import annotations

from app.domain.lexicon.phoneme_codec import decode_phoneme_field
from app.utils.jyutping_codec import rhyme_finals_from_jyutping


def get_word_text(word) -> str:
    if isinstance(word, dict):
        return word.get("char") or ""
    return getattr(word, "char", "") or ""


def get_word_jyutping(word) -> str:
    if isinstance(word, dict):
        return word.get("jyutping") or ""
    return getattr(word, "jyutping", "") or ""


def get_word_parts(word, field: str) -> list:
    dim = "final" if field == "finals" else "initial"
    if isinstance(word, dict):
        raw = word.get(field)
    else:
        raw = getattr(word, field, None)
    # word_cache / transient SimpleNamespace may store already-decoded lists
    if isinstance(raw, list):
        return [str(x) if x is not None else "" for x in raw]
    return decode_phoneme_field(raw, dim)  # type: ignore[arg-type]

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
