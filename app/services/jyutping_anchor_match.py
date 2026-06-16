"""粵拼錨比對：韻母片段 finals 解析與逐格比對。"""

from __future__ import annotations

import json
from functools import lru_cache

from app.services.jyutping_anchor import STANDALONE_NG, normalize_rhyme_letters
from app.services.jyutping_match import _parse_syllable_token, parse_word_jyutping
from app.services.word_serializer import get_word_jyutping, get_word_parts


def _word_rhyme_finals(word):
    from app.services.word_serializer import get_rhyme_finals

    return get_rhyme_finals(word)


def syllable_matches_rhyme_fragment(syl_letters: str, fragment: str) -> bool:
    fragment = normalize_rhyme_letters(fragment)
    syl_letters = syl_letters.lower()
    if fragment == STANDALONE_NG:
        return syl_letters in ("m", "ng")
    return syl_letters == fragment or syl_letters.endswith(fragment)


@lru_cache(maxsize=256)
def rhyme_letter_final_options(letters: str) -> frozenset[str]:
    """從 rime 預設讀音推導韻母片段對應嘅 finals 集合；空集表示無效錨。"""
    from app.lexicon.rime_char_index import _entries_by_char, ensure_rime_char_loaded
    from app.utils.jyutping_codec import split_jyutping

    letters = normalize_rhyme_letters(letters)
    ensure_rime_char_loaded()
    finals: set[str] = set()
    for entries in _entries_by_char.values():
        for entry in entries:
            token = entry.jyutping.split()[0]
            syl = _parse_syllable_token(token)
            if not syl or not syllable_matches_rhyme_fragment(syl.letters, letters):
                continue
            finals_json = split_jyutping(token)[1]
            try:
                arr = json.loads(finals_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if arr:
                finals.add(str(arr[0]))
    return frozenset(finals)


def rhyme_letters_resolve_ok(letters: str) -> bool:
    return bool(rhyme_letter_final_options(letters))


def matches_rhyme_letters_at_position(word, pos: int, letters: str, db) -> bool:
    options = rhyme_letter_final_options(letters)
    if not options:
        return False
    parts = _word_rhyme_finals(word)
    if pos >= len(parts):
        return False
    if parts[pos] in options:
        return True
    jyut = get_word_jyutping(word)
    syls = parse_word_jyutping(jyut)
    if pos < len(syls) and syllable_matches_rhyme_fragment(syls[pos].letters, letters):
        return True
    return False


def matches_syllable_letters_at_position(word, pos: int, letters: str, db) -> bool:
    syls = parse_word_jyutping(get_word_jyutping(word))
    if pos >= len(syls):
        return False
    return syls[pos].letters == letters.lower()


def matches_initial_letters_at_position(word, pos: int, letter: str, db) -> bool:
    parts = get_word_parts(word, "initials")
    return pos < len(parts) and parts[pos] == letter.lower()


def matches_jyutping_anchor_at_position(
    word,
    pos: int,
    kind: str,
    value: str,
    db,
) -> bool:
    if kind == "rhyme_letters":
        return matches_rhyme_letters_at_position(word, pos, value, db)
    if kind == "syllable_letters":
        return matches_syllable_letters_at_position(word, pos, value, db)
    if kind == "initial_letters":
        return matches_initial_letters_at_position(word, pos, value, db)
    return False
