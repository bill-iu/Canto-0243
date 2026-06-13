"""粵拼查詢：精準音節比對（非子字串模糊）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

TONE_DIGITS = frozenset("123456")
_JYUTPING_QUERY_RE = re.compile(r"^[a-zA-Z0-9\s]+$")


@dataclass(frozen=True)
class JyutSyllable:
    letters: str
    tone: Optional[int] = None


def is_jyutping_query(q: str) -> bool:
    """查詢是否為粵拼輸入（含字母、無漢字）。"""
    if not q or not q.strip():
        return False
    if re.search(r"[\u4e00-\u9fff]", q):
        return False
    return bool(re.search(r"[a-zA-Z]", q)) and bool(_JYUTPING_QUERY_RE.match(q.strip()))


def parse_jyutping_query(q: str) -> Optional[List[JyutSyllable]]:
    """將查詢字串拆成音節；格式不合法時返回 None。"""
    if not is_jyutping_query(q):
        return None

    syllables: List[JyutSyllable] = []
    for token in q.strip().lower().split():
        parsed = _parse_syllable_token(token)
        if parsed is None:
            return None
        syllables.append(parsed)

    return syllables or None


def parse_word_jyutping(jyutping: str) -> List[JyutSyllable]:
    if not jyutping or not str(jyutping).strip():
        return []

    out: List[JyutSyllable] = []
    for token in jyutping.strip().lower().split():
        parsed = _parse_syllable_token(token)
        if parsed is not None:
            out.append(parsed)
    return out


def normalize_jyutping(jyutping: str) -> str:
    return " ".join(jyutping.strip().lower().split())


def matches_jyutping_query(word_jyutping: str, query: str) -> bool:
    """詞條粵拼是否符合粵拼查詢規則。"""
    query_syllables = parse_jyutping_query(query)
    if not query_syllables:
        return False

    word_syllables = parse_word_jyutping(word_jyutping)
    if len(word_syllables) != len(query_syllables):
        return False

    if all(s.tone is not None for s in query_syllables):
        return normalize_jyutping(word_jyutping) == normalize_jyutping(query)

    for word_syl, query_syl in zip(word_syllables, query_syllables):
        if word_syl.letters != query_syl.letters:
            return False
        if query_syl.tone is not None and word_syl.tone != query_syl.tone:
            return False
    return True


def expected_word_length(query: str) -> Optional[int]:
    """查詢對應的字面音節數；單音節無調只查單字。"""
    syllables = parse_jyutping_query(query)
    if not syllables:
        return None
    if len(syllables) == 1 and syllables[0].tone is None:
        return 1
    return len(syllables)


def _parse_syllable_token(token: str) -> Optional[JyutSyllable]:
    token = token.strip().lower()
    if not token:
        return None

    tone: Optional[int] = None
    letters = token
    if token[-1] in TONE_DIGITS:
        tone = int(token[-1])
        letters = token[:-1]

    if not letters or not letters.isalpha():
        return None
    return JyutSyllable(letters=letters, tone=tone)


__all__ = [
    "JyutSyllable",
    "expected_word_length",
    "is_jyutping_query",
    "matches_jyutping_query",
    "normalize_jyutping",
    "parse_jyutping_query",
    "parse_word_jyutping",
]
