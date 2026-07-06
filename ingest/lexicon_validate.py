"""Trust-boundary checks for word-level lexicon readings (CONTEXT § 詞級標音格式門檻)."""
from __future__ import annotations

import re

from app.services.jyutping_match import parse_word_jyutping
from app.utils.jyutping_codec import get_0243_code

_CJK_CHAR = re.compile(r"[\u3400-\u9fff]")
_LATIN_ALNUM = re.compile(r"[A-Za-z0-9]")


def _looks_like_mixed_literal(literal: str) -> bool:
    text = str(literal or "").strip()
    if not text:
        return False
    has_cjk = bool(_CJK_CHAR.search(text))
    has_alnum = bool(_LATIN_ALNUM.search(text))
    return has_cjk and has_alnum


def _literal_positions(literal: str) -> list[str]:
    return [ch for ch in str(literal or "") if ch.isalnum() or _CJK_CHAR.match(ch)]


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
    for index, char in enumerate(text):
        if not (char.isalnum() or _CJK_CHAR.match(char)):
            continue
        if _CJK_CHAR.match(char):
            syllable = syllables[len(code_chars)]
            code_chars.append(get_0243_code(syllable) or "?")
        elif char.isdigit():
            code_chars.append(char)
        else:
            code_chars.append("?")
    return "".join(code_chars)


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
    han_chars = [ch for ch in literal if _CJK_CHAR.match(ch)]
    if len(tokens) != len(han_chars):
        return False
    syllables = parse_word_jyutping(jp)
    if len(syllables) != len(han_chars):
        return False
    if any(s.tone is None for s in syllables):
        return False
    code = get_0243_code(jp)
    return bool(code) and "?" not in code
