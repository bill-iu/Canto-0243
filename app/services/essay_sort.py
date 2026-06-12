"""Essay corpus frequency tie-break for search result ordering."""

from __future__ import annotations

from app.lexicon.curated_index import curated_sort_boost
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.word_serializer import get_word_jyutping, get_word_text


def default_word_sort_key(word) -> tuple:
    """Curated > essay freq > pron_rank > char > jyutping."""
    ch = get_word_text(word)
    jyut = get_word_jyutping(word)
    return (
        -curated_sort_boost(ch),
        -get_essay_frequency(ch),
        pron_rank_sort_value_for_word(ch, jyut),
        ch,
        jyut,
    )
