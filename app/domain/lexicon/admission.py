"""詞庫收錄決策 — CONTEXT § 詞庫埠 / 多字收錄 / 單字收錄 / 音節拼接讀音。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from app.lexicon.static_index import LexiconEntry
from app.services.lexicon_port import LexiconPort, default_lexicon_port
from app.utils.syllable_reading import compose_lexicon_entries_from_rime


class AdmissionSource(str, Enum):
    NONE = "none"
    SINGLE_CHAR_RIME = "single_char_rime"
    MULTI_CHAR_LEXICON = "multi_char_lexicon"
    SYLLABLE_COMPOSE = "syllable_compose"


@dataclass(frozen=True)
class AdmissionResult:
    literal: str
    source: AdmissionSource
    entries: List[LexiconEntry]

    @property
    def can_inject(self) -> bool:
        return bool(self.entries)


def _composite_literal_entries(text: str) -> tuple[List[LexiconEntry], bool, bool]:
    from app.lexicon.rime_char_index import get_rime_char_entries
    from app.lexicon.static_index import get_lexicon_entries

    if len(text) == 1:
        entries = get_rime_char_entries(text)
        return entries, False, False
    static_entries = get_lexicon_entries(text)
    if static_entries:
        return static_entries, True, False
    composed = compose_lexicon_entries_from_rime(text)
    return composed, False, bool(composed)


def _entries_for_literal(text: str, lexicon: LexiconPort) -> tuple[List[LexiconEntry], bool, bool]:
    from app.lexicon.static_index import get_lexicon_entries
    from app.services.lexicon_port import CompositeLexicon, Static0243Lexicon

    if isinstance(lexicon, CompositeLexicon):
        return _composite_literal_entries(text)

    if isinstance(lexicon, Static0243Lexicon):
        entries = get_lexicon_entries(text)
        return entries, bool(entries and len(text) >= 2), False

    entries = list(lexicon.get_entries(text))
    if entries:
        return entries, len(text) >= 2, False
    if len(text) >= 2:
        composed = compose_lexicon_entries_from_rime(text)
        return composed, False, bool(composed)
    return [], False, False


def _classify_source(
    text: str,
    entries: List[LexiconEntry],
    *,
    from_static: bool,
    from_compose: bool,
) -> AdmissionSource:
    if not entries:
        return AdmissionSource.NONE
    if len(text) == 1:
        return AdmissionSource.SINGLE_CHAR_RIME
    if from_static:
        return AdmissionSource.MULTI_CHAR_LEXICON
    if from_compose:
        return AdmissionSource.SYLLABLE_COMPOSE
    return AdmissionSource.MULTI_CHAR_LEXICON


def resolve_admission(
    literal: str,
    *,
    lexicon: Optional[LexiconPort] = None,
) -> AdmissionResult:
    text = (literal or "").strip()
    if not text or not re.search(r"[\u4e00-\u9fff]", text):
        return AdmissionResult(text, AdmissionSource.NONE, [])

    port = lexicon or default_lexicon_port()
    port.ensure_loaded()
    entries, from_static, from_compose = _entries_for_literal(text, port)
    source = _classify_source(
        text, entries, from_static=from_static, from_compose=from_compose
    )
    return AdmissionResult(text, source, entries)


__all__ = [
    "AdmissionResult",
    "AdmissionSource",
    "resolve_admission",
]
