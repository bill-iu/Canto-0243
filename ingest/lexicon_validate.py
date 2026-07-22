"""Trust-boundary checks for word-level lexicon readings (CONTEXT § 詞級標音格式門檻)."""
from __future__ import annotations

import re

from app.services.jyutping_match import parse_word_jyutping
from app.utils.han import HAN_RE, is_han_char
from app.utils.jyutping_codec import get_0243_code

_CJK_CHAR = HAN_RE
_LATIN_ALNUM = re.compile(r"[A-Za-z0-9]")


def _looks_like_mixed_literal(literal: str) -> bool:
    text = str(literal or "").strip()
    if not text:
        return False
    has_cjk = bool(_CJK_CHAR.search(text))
    has_alnum = bool(_LATIN_ALNUM.search(text))
    return has_cjk and has_alnum


def _literal_positions(literal: str) -> list[str]:
    return [ch for ch in str(literal or "") if ch.isalnum() or is_han_char(ch)]


def _generate_mixed_literal_jyutping(text: str) -> str | None:
    try:
        from pyjyutping import jyutping
    except Exception:
        return None
    try:
        reading = jyutping.convert(text)
    except Exception:
        return None
    reading = str(reading or "").strip()
    return reading or None


def build_mixed_literal_code(literal: str, jyutping: str) -> str:
    text = str(literal or "").strip()
    jp = str(jyutping or "").strip()
    if not text or not jp or not _looks_like_mixed_literal(text):
        return ""
    positions = _literal_positions(text)
    syllables = jp.split()
    if len(syllables) != len(positions):
        return ""
    code_chars: list[str] = []
    for char in text:
        if not (char.isalnum() or is_han_char(char)):
            continue
        if is_han_char(char):
            syllable = syllables[len(code_chars)]
            code_chars.append(get_0243_code(syllable) or "?")
        elif char.isdigit():
            code_chars.append(char)
        else:
            code_chars.append("?")
    return "".join(code_chars)


def normalize_lexicon_candidate(
    literal: str,
    jyutping: str,
    *,
    code: str | None = None,
) -> tuple[str, str, str] | None:
    text = str(literal or "").strip()
    jp = str(jyutping or "").strip()
    if not text or not jp:
        return None
    if _looks_like_mixed_literal(text):
        if not is_valid_word_lexicon_reading(text, jp, allow_mixed_literal=True):
            return None
        normalized_code = str(code or "").strip() or build_mixed_literal_code(text, jp) or ""
        if not normalized_code:
            return None
        return text, jp, normalized_code
    if len(text) >= 2 and not is_valid_word_lexicon_reading(text, jp):
        return None
    normalized_code = str(code or "").strip() or get_0243_code(jp) or ""
    if not normalized_code:
        return None
    return text, jp, normalized_code


def is_valid_word_lexicon_reading(char: str, jyutping: str, *, allow_mixed_literal: bool = False) -> bool:
    literal = str(char or "").strip()
    jp = str(jyutping or "").strip()
    if not literal or not jp:
        return False
    tokens = jp.split()
    if not tokens:
        return False
    if allow_mixed_literal and _looks_like_mixed_literal(literal):
        positions = _literal_positions(literal)
        if len(tokens) != len(positions):
            return False
        syllables = parse_word_jyutping(jp)
        if len(syllables) != len(positions):
            return False
        if any(s.tone is None for s in syllables):
            return False
        code = build_mixed_literal_code(literal, jp)
        return bool(code)
    han_chars = [ch for ch in literal if is_han_char(ch)]
    if len(tokens) != len(han_chars):
        return False
    syllables = parse_word_jyutping(jp)
    if len(syllables) != len(han_chars):
        return False
    if any(s.tone is None for s in syllables):
        return False
    code = get_0243_code(jp)
    return bool(code) and "?" not in code
