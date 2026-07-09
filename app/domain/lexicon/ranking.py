"""詞條排序信號 — CONTEXT § 詞條排序信號 / 搜尋結果排序 / 等號參考讀音選列。"""

from __future__ import annotations

from typing import Any, Iterable, List, TypeVar

from app.lexicon.curated_index import curated_sort_boost
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.domain.lexicon.word_row import get_word_jyutping, get_word_text

T = TypeVar("T")


def _is_pure_han_text(text: str) -> bool:
    return bool(text) and all("\u4e00" <= ch <= "\u9fff" for ch in text)


def _rank_tier(text: str) -> int:
    if _is_pure_han_text(text):
        return 0
    if bool(text) and any("\u4e00" <= ch <= "\u9fff" for ch in text) and any(ch.isalnum() for ch in text):
        return 1
    return 2


def _is_aa_variant_jyutping(jyutping: str) -> bool:
    return "aa" in (jyutping or "").lower()


def search_result_sort_key(word) -> tuple:
    """扁平搜尋結果排序：純漢字 → essay → curated → pron_rank → 字面。"""
    ch = get_word_text(word)
    jyut = get_word_jyutping(word)
    han_tier = _rank_tier(ch)
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
    han_tier = _rank_tier(ch)
    return (
        han_tier,
        -get_essay_frequency(ch),
        -curated_sort_boost(ch),
        ch,
        jyut,
    )


def sort_search_results(words: Iterable[T]) -> List[T]:
    return sorted(words, key=search_result_sort_key)


def ranking_logic_self_check() -> None:
    """Self-check: search_result_sort_key + heteronym_sort_key.

    heteronym: essay/curated freq primary for char order; pure jyut lexical (no pron_rank) within char.
    """
    class W:
        def __init__(self, c: str, j: str = "") -> None:
            self.char = c
            self.jyutping = j

    # real essay: 我 (millions) >> 屎 (~35k); within-char jyut lexical asc
    w_h1 = W("我", "ngo5")
    w_h2 = W("我", "ngo1")
    w_l = W("屎", "si2")
    s = sorted([w_l, w_h1, w_h2], key=heteronym_sort_key)
    chs = [x.char for x in s]
    assert chs == ["我", "我", "屎"], chs
    jys = [x.jyutping for x in s if x.char == "我"]
    assert jys == ["ngo1", "ngo5"], jys  # lexical, skip pron
    print("ranking_logic_self_check: heteronym freq+lexical OK")
