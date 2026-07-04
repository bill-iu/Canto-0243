"""詞條排序信號 — CONTEXT § 詞條排序信號 / 搜尋結果排序 / 等號參考讀音選列。"""

from __future__ import annotations

from typing import Any, Iterable, List, TypeVar

from app.lexicon.curated_index import curated_sort_boost
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.word_serializer import get_word_jyutping, get_word_text

T = TypeVar("T")


def _is_pure_han_text(text: str) -> bool:
    return bool(text) and all("\u4e00" <= ch <= "\u9fff" for ch in text)


def _is_aa_variant_jyutping(jyutping: str) -> bool:
    return "aa" in (jyutping or "").lower()


def search_result_sort_key(word) -> tuple:
    """扁平搜尋結果排序：純漢字 → essay → curated → pron_rank → 字面。"""
    ch = get_word_text(word)
    jyut = get_word_jyutping(word)
    han_tier = 0 if _is_pure_han_text(ch) else 1
    return (
        han_tier,
        -get_essay_frequency(ch),
        -curated_sort_boost(ch),
        pron_rank_sort_value_for_word(ch, jyut),
        ch,
        jyut,
    )


def authoritative_reading_sort_key(row: Any) -> tuple:
    """等號參考讀音選列：pron_rank → essay → 略過 aa → 粵拼序。"""
    char = get_word_text(row)
    jyut = get_word_jyutping(row)
    return (
        pron_rank_sort_value_for_word(char, jyut),
        -get_essay_frequency(char),
        1 if _is_aa_variant_jyutping(jyut) else 0,
        jyut or "",
    )


def literal_priority_sort_key(word, literal_positions: list[tuple[int, str]]) -> tuple:
    """缺字查詢字面優先：吻合數前綴 + 扁平搜尋結果排序。"""
    char = get_word_text(word)
    exact_count = sum(1 for pos, ch in literal_positions if pos < len(char) and char[pos] == ch)
    return (-exact_count, *search_result_sort_key(word))


def heteronym_sort_key(word) -> tuple:
    """同音異讀查詢專用：頻率部分（同搜尋結果排序） + 字面 + 粵拼（不含 pron_rank）。
    以實現不同字面按常用字詞頻排序，同字面內讀音恢復純粵拼 lexical 排序。
    """
    ch = get_word_text(word)
    jyut = get_word_jyutping(word)
    han_tier = 0 if _is_pure_han_text(ch) else 1
    return (
        han_tier,
        -get_essay_frequency(ch),
        -curated_sort_boost(ch),
        ch,
        jyut,
    )


def sort_search_results(words: Iterable[T]) -> List[T]:
    return sorted(words, key=search_result_sort_key)