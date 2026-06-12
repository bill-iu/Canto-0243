"""Essay corpus frequency tie-break for search result ordering."""

from __future__ import annotations

from typing import Iterable, List, TypeVar

from app.lexicon.curated_index import curated_sort_boost
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.word_serializer import get_word_jyutping, get_word_text

T = TypeVar("T")


def is_pure_han_text(text: str) -> bool:
    return bool(text) and all("\u4e00" <= ch <= "\u9fff" for ch in text)


def default_word_sort_key(word) -> tuple:
    """Pure Han > essay freq > curated > pron_rank > char > jyutping (CONTEXT.md)."""
    ch = get_word_text(word)
    jyut = get_word_jyutping(word)
    han_tier = 0 if is_pure_han_text(ch) else 1
    return (
        han_tier,
        -get_essay_frequency(ch),
        -curated_sort_boost(ch),
        pron_rank_sort_value_for_word(ch, jyut),
        ch,
        jyut,
    )


def sort_words(words: Iterable[T]) -> List[T]:
    return sorted(words, key=default_word_sort_key)


# Backward-compatible alias (pure digit uses unified key).
pure_digit_sort_key = default_word_sort_key
