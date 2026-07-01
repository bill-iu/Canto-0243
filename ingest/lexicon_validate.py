"""Trust-boundary checks for word-level lexicon readings (CONTEXT § 詞級標音格式門檻)."""
from __future__ import annotations

from app.services.jyutping_match import parse_word_jyutping
from app.utils.jyutping_codec import get_0243_code


def is_valid_word_lexicon_reading(char: str, jyutping: str) -> bool:
    literal = str(char or "").strip()
    jp = str(jyutping or "").strip()
    if not literal or not jp:
        return False
    tokens = jp.split()
    if len(tokens) != len(literal):
        return False
    syllables = parse_word_jyutping(jp)
    if len(syllables) != len(literal):
        return False
    if any(s.tone is None for s in syllables):
        return False
    code = get_0243_code(jp)
    return bool(code) and "?" not in code
