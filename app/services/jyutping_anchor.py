"""粵拼錨：缺字家族內拉丁錨解析（CONTEXT § 粵拼錨）。"""

from __future__ import annotations

import re
from typing import Literal, Optional

from app.services.jyutping_match import _parse_syllable_token

VOWEL_RHYME_LETTERS = frozenset("aeioum")
STANDALONE_NG = "ng"

AnchorKind = Literal["initial_letters", "rhyme_letters", "syllable_letters"]


def _is_complete_syllable_in_rime(letters: str) -> bool:
    """粵拼錨：僅當 rime 預設讀音存在完整音節 letters 時先當 syllable_letters。"""
    from app.lexicon.rime_char_index import _entries_by_char, ensure_rime_char_loaded

    text = letters.strip().lower()
    ensure_rime_char_loaded()
    for entries in _entries_by_char.values():
        for entry in entries:
            syl = _parse_syllable_token(entry.jyutping.split()[0])
            if syl and syl.letters == text:
                return True
    return False


def classify_latin_anchor(letters: str) -> Optional[AnchorKind]:
    """G4：單母音/m、獨立 ng→韻母；rime 完整音節→syllable；單輔音→聲母；其餘→韻母片段。"""
    from app.lexicon.rime_char_index import ensure_rime_char_loaded

    ensure_rime_char_loaded()
    text = (letters or "").strip().lower()
    if not text or not text.isalpha():
        return None
    if text in VOWEL_RHYME_LETTERS or text == STANDALONE_NG:
        return "rhyme_letters"
    if len(text) == 1:
        return "initial_letters"
    if _is_complete_syllable_in_rime(text):
        return "syllable_letters"
    return "rhyme_letters"


def normalize_rhyme_letters(letters: str) -> str:
    """m 與獨立 ng 完全等價。"""
    text = letters.strip().lower()
    if text == "m":
        return STANDALONE_NG
    return text


def parse_triple_jyutping_slot_query(q: str) -> Optional[dict]:
    """?{拉丁}? — 三格；中格粵拼錨。"""
    m = re.match(r"^(\?)([a-zA-Z]+)(\?)$", q)
    if not m:
        return None
    letters = m.group(2)
    kind = classify_latin_anchor(letters)
    if kind is None:
        return None
    return {
        "raw_q": q,
        "width": 3,
        "anchor_pos": 1,
        "anchor_kind": kind,
        "anchor_value": normalize_rhyme_letters(letters.lower()),
    }


def parse_end_jyutping_syllable_query(q: str) -> Optional[dict]:
    """?{音節} — 二字末格完整音節（?hon）。"""
    m = re.match(r"^(\?)([a-zA-Z]+)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "syllable_letters":
        return None
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 1,
        "anchor_kind": "syllable_letters",
        "anchor_value": letters,
    }


def parse_code_syllable_three_query(q: str) -> Optional[dict]:
    """{首碼}?{音節}{末碼} — 三字碼音節（3?hon4）。"""
    m = re.match(r"^(\d)\?([a-zA-Z]+)(\d)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "syllable_letters":
        return None
    return {
        "raw_q": q,
        "width": 3,
        "anchor_pos": 1,
        "anchor_kind": "syllable_letters",
        "anchor_value": letters,
        "code_prefix": m.group(1) + m.group(3),
        "code_slots": [(0, m.group(1)), (2, m.group(3))],
    }


def parse_code_syllable_two_query(q: str) -> Optional[dict]:
    """{首碼}{音節}{末碼} — 二字碼音節（3hon4），無中間 ?。"""
    m = re.match(r"^(\d)([a-zA-Z]+)(\d)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "syllable_letters":
        return None
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "syllable_letters",
        "anchor_value": letters,
        "code_prefix": m.group(1) + m.group(3),
    }


def parse_code_initial_query(q: str) -> Optional[dict]:
    """{首碼}{輔音}{末碼} — 聲母錨（3h4）。"""
    m = re.match(r"^(\d)([a-z])(\d)$", q)
    if not m:
        return None
    letter = m.group(2).lower()
    if classify_latin_anchor(letter) != "initial_letters":
        return None
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "initial_letters",
        "anchor_value": letter,
        "code_prefix": m.group(1) + m.group(3),
        "equals_style": True,
    }


def parse_code_rhyme_equals_query(q: str) -> Optional[dict]:
    """{左碼}{韻母}{右碼} — 碼夾韻母（23ei0 ↔ 23你=0）。"""
    m = re.match(r"^(\d+)([a-zA-Z]+)(\d+)$", q)
    if not m:
        return None
    left, letters, right = m.group(1), m.group(2).lower(), m.group(3)
    if len(left) < 1 or len(right) < 1:
        return None
    if classify_latin_anchor(letters) != "rhyme_letters":
        return None
    width = len(left) + len(right)
    return {
        "raw_q": q,
        "width": width,
        "anchor_pos": max(0, len(left) - 1),
        "anchor_kind": "rhyme_letters",
        "anchor_value": normalize_rhyme_letters(letters),
        "code_prefix": left + right,
        "equals_style": True,
    }


def parse_hybrid_jyutping_syllable_query(q: str) -> Optional[dict]:
    """{碼}{音節} — 碼後音節錨末格（23ngo）。"""
    m = re.match(r"^(\d+)([a-zA-Z]+)$", q)
    if not m or "?" in q:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "syllable_letters":
        return None
    prefix = m.group(1)
    return {
        "raw_q": q,
        "width": len(prefix),
        "anchor_pos": len(prefix) - 1,
        "anchor_kind": "syllable_letters",
        "anchor_value": letters,
        "code_prefix": prefix,
    }


def parse_rhyme_vowel_hybrid_query(q: str) -> Optional[dict]:
    """{碼}{母音} — 碼後韻母錨末格（23o）。"""
    m = re.match(r"^(\d+)([a-zA-Z]+)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "rhyme_letters":
        return None
    prefix = m.group(1)
    return {
        "raw_q": q,
        "width": len(prefix),
        "anchor_pos": len(prefix) - 1,
        "anchor_kind": "rhyme_letters",
        "anchor_value": normalize_rhyme_letters(letters),
        "code_prefix": prefix,
        "hybrid_rhyme": True,
    }


def parse_jyutping_anchor_query(q: str) -> Optional[dict]:
    if not q or re.search(r"[\u4e00-\u9fff]", q):
        return None
    from app.lexicon.rime_char_index import ensure_rime_char_loaded

    ensure_rime_char_loaded()
    for parser in (
        parse_triple_jyutping_slot_query,
        parse_end_jyutping_syllable_query,
        parse_code_syllable_three_query,
        parse_code_initial_query,
        parse_code_syllable_two_query,
        parse_code_rhyme_equals_query,
        parse_hybrid_jyutping_syllable_query,
        parse_rhyme_vowel_hybrid_query,
    ):
        parsed = parser(q)
        if parsed:
            return parsed
    return None


def is_jyutping_anchor_mask_query(q: str) -> bool:
    return parse_jyutping_anchor_query(q) is not None
