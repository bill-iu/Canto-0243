"""Syllable-composed readings from rime per-char defaults (CONTEXT § 音節拼接讀音)."""

from __future__ import annotations

import re

from app.lexicon.rime_char_index import get_rime_char_entries
from app.lexicon.static_index import LexiconEntry
from app.utils.jyutping_codec import get_0243_code

_CANTO_RE = re.compile(r"[\u4e00-\u9fff]")


def compose_lexicon_entries_from_rime(text: str) -> list[LexiconEntry]:
    """
    Build one LexiconEntry by concatenating each character's rime 預設 reading.
    Returns [] if any character lacks a rime default or text is not multi-canto chars.
    """
    text = (text or "").strip()
    if len(text) < 2:
        return []
    if not _CANTO_RE.search(text) or any(not _CANTO_RE.fullmatch(ch) for ch in text):
        return []

    syllables: list[str] = []
    for ch in text:
        entries = get_rime_char_entries(ch)
        if not entries:
            return []
        syllables.append(entries[0].jyutping)

    jyut_str = " ".join(syllables)
    code = get_0243_code(jyut_str) or ""
    if not code:
        return []
    return [LexiconEntry(char=text, jyutping=jyut_str, code=code)]


__all__ = ["compose_lexicon_entries_from_rime"]
