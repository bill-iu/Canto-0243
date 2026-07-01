"""粵拼錨：缺字家族內拉丁錨解析與比對（CONTEXT § 粵拼錨）。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Literal, Optional

from app.services.jyutping_match import _parse_syllable_token, parse_word_jyutping
from app.services.query_tokens import CODE_TAIL_MIDDLE
from app.services.word_serializer import get_rhyme_finals, get_word_jyutping, get_word_parts

_SLOT = re.escape(CODE_TAIL_MIDDLE)

from app.utils.jyutping_codec import (
    STANDALONE_NASAL_FINALS,
    is_standalone_nasal_syllable_token,
    rhyme_final_index_keys_per_position,
    syllable_token_at,
)

VOWEL_RHYME_LETTERS = frozenset("aeiou")
STANDALONE_NG = "ng"
AMBIGUOUS_PHONEME_LETTERS = frozenset({"m", "ng"})
INITIAL_CLUSTERS = frozenset({"ng", "gw", "kw"})

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
    """G4：單母音、獨立 ng→韻母；rime 完整音節→syllable；單輔音→聲母；其餘→韻母片段。"""
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


def _is_hybrid_rhyme_letters(letters: str) -> bool:
    text = (letters or "").strip().lower()
    if text in VOWEL_RHYME_LETTERS or text in AMBIGUOUS_PHONEME_LETTERS:
        return True
    return classify_latin_anchor(text) == "rhyme_letters"


def default_syllable_letters_for_anchor_char(char: str) -> Optional[str]:
    """漢字完整音節錨：rime 預設讀音嘅音節字母（唔含聲調）。"""
    from app.lexicon.rime_char_index import get_rime_char_entries

    entries = get_rime_char_entries(char)
    if not entries:
        return None
    token = (entries[0].jyutping or "").split()[0]
    syl = _parse_syllable_token(token)
    return syl.letters if syl else None


def normalize_hanzi_dollar_syllable_anchors(q: str) -> str:
    """`$`+單漢字 → 拉丁完整音節字母；保留 `$$` 供同音節疊字查詢。"""
    if not q or "$" not in q:
        return q
    out: list[str] = []
    i = 0
    while i < len(q):
        if q[i] == "$" and i + 1 < len(q) and q[i + 1] == "$":
            out.append("$$")
            i += 2
            continue
        if q[i] == "$" and i + 1 < len(q) and re.fullmatch(r"[一-龥]", q[i + 1]):
            letters = default_syllable_letters_for_anchor_char(q[i + 1])
            if letters:
                out.append(letters)
                i += 2
                continue
        out.append(q[i])
        i += 1
    return "".join(out)


def parse_dual_phoneme_anchor_query(q: str) -> Optional[dict]:
    """歧義粵拼錨：m／ng 碼夾或三格中格 → 雙列（ADR-0009）。"""
    m = re.match(rf"^(\?){_SLOT}?([a-zA-Z]+)(\?)$", q)
    if m:
        letters = m.group(2).lower()
        if letters in AMBIGUOUS_PHONEME_LETTERS:
            return {
                "raw_q": q,
                "width": 3,
                "anchor_pos": 1,
                "anchor_kind": "rhyme_letters",
                "anchor_value": normalize_rhyme_letters(letters),
                "dual_phoneme": True,
                "dual_initial_value": letters,
            }
    m = re.match(r"^(\d+)(m|ng)(\d+)$", q, re.IGNORECASE)
    if m:
        left, letters, right = m.group(1), m.group(2).lower(), m.group(3)
        return {
            "raw_q": q,
            "width": len(left) + len(right),
            "anchor_pos": max(0, len(left) - 1),
            "anchor_kind": "rhyme_letters",
            "anchor_value": normalize_rhyme_letters(letters),
            "code_prefix": left + right,
            "equals_style": True,
            "dual_phoneme": True,
            "dual_initial_value": letters,
        }
    return None


def parse_code_cluster_initial_query(q: str) -> Optional[dict]:
    """{首碼}{ng|gw|kw}{末碼} — 雙聲母錨（ng 歧義由 dual parser 處理）。"""
    m = re.match(r"^(\d)(ng|gw|kw)(\d)$", q, re.IGNORECASE)
    if not m:
        return None
    cluster = m.group(2).lower()
    if cluster == "ng":
        return None
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "initial_letters",
        "anchor_value": cluster,
        "code_prefix": m.group(1) + m.group(3),
        "equals_style": True,
    }


def normalize_rhyme_letters(letters: str) -> str:
    """m 與獨立 ng 完全等價。"""
    text = letters.strip().lower()
    if text == "m":
        return STANDALONE_NG
    return text


def parse_triple_jyutping_slot_query(q: str) -> Optional[dict]:
    """?{拉丁}? / ?+{拉丁}? — 三格；中格粵拼錨。"""
    m = re.match(rf"^(\?){_SLOT}?([a-zA-Z]+)(\?)$", q)
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
    """?{音節} / ?+{音節} — 二字末格完整音節（?hon）。"""
    m = re.match(rf"^(\?){_SLOT}?([a-zA-Z]+)$", q)
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
    """{首碼}?{音節}{末碼} / {首碼}+{音節}{末碼} — 三字碼音節（3+hon4）。"""
    m = re.match(rf"^(\d)[\?{_SLOT}]([a-zA-Z]+)(\d)$", q)
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


def parse_code_rhyme_three_query(q: str) -> Optional[dict]:
    """{首碼}+{韻母}{末碼} / {首碼}?{韻母}{末碼} — 三字中格韻母（3+an4 ↔ 3+人=4）。"""
    m = re.match(rf"^(\d)[\?{_SLOT}]([a-zA-Z]+)(\d)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if classify_latin_anchor(letters) != "rhyme_letters":
        return None
    return {
        "raw_q": q,
        "width": 3,
        "anchor_pos": 1,
        "anchor_kind": "rhyme_letters",
        "anchor_value": normalize_rhyme_letters(letters),
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
    if not m or CODE_TAIL_MIDDLE in q:
        return None
    letters = m.group(2).lower()
    if not _is_hybrid_rhyme_letters(letters):
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


def parse_code_rhyme_plus_tail_query(q: str) -> Optional[dict]:
    """{碼}+{韻母} — 三字碼尾韻母錨（23+o ↔ 23+我=）。"""
    m = re.match(rf"^(\d+){_SLOT}([a-zA-Z]+)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if not _is_hybrid_rhyme_letters(letters):
        return None
    code = m.group(1)
    return {
        "raw_q": q,
        "width": len(code) + 1,
        "anchor_pos": len(code),
        "anchor_kind": "rhyme_letters",
        "anchor_value": normalize_rhyme_letters(letters),
        "code_prefix": code,
        "code_slots": [(i, d) for i, d in enumerate(code)],
        "hybrid_rhyme": True,
    }


def parse_jyutping_anchor_query(q: str) -> Optional[dict]:
    if not q or re.search(r"[\u4e00-\u9fff]", q):
        return None
    from app.lexicon.rime_char_index import ensure_rime_char_loaded

    ensure_rime_char_loaded()
    for parser in (
        parse_dual_phoneme_anchor_query,
        parse_triple_jyutping_slot_query,
        parse_end_jyutping_syllable_query,
        parse_code_syllable_three_query,
        parse_code_rhyme_three_query,
        parse_code_cluster_initial_query,
        parse_code_initial_query,
        parse_code_syllable_two_query,
        parse_code_rhyme_equals_query,
        parse_code_rhyme_plus_tail_query,
        parse_hybrid_jyutping_syllable_query,
        parse_rhyme_vowel_hybrid_query,
    ):
        parsed = parser(q)
        if parsed:
            return parsed
    return None


def is_jyutping_anchor_mask_query(q: str) -> bool:
    return parse_jyutping_anchor_query(q) is not None


def syllable_matches_rhyme_fragment(syl_letters: str, fragment: str) -> bool:
    from app.utils.jyutping_codec import split_jyutping

    fragment = normalize_rhyme_letters(fragment)
    syl_letters = syl_letters.lower()
    if fragment == STANDALONE_NG:
        return syl_letters in ("m", "ng")
    if len(fragment) == 1:
        finals_json = split_jyutping(syl_letters)[1]
        try:
            arr = json.loads(finals_json)
        except (TypeError, json.JSONDecodeError):
            arr = []
        return bool(arr) and str(arr[0]) == fragment
    return syl_letters == fragment or syl_letters.endswith(fragment)


@lru_cache(maxsize=256)
def rhyme_letter_final_options(letters: str) -> frozenset[str]:
    """從 rime 預設讀音推導韻母片段對應嘅 finals 集合；空集表示無效錨。"""
    from app.lexicon.rime_char_index import _entries_by_char, ensure_rime_char_loaded
    from app.utils.jyutping_codec import split_jyutping

    letters = normalize_rhyme_letters(letters)
    if letters == STANDALONE_NG:
        return frozenset(STANDALONE_NASAL_FINALS)
    ensure_rime_char_loaded()
    finals: set[str] = set()
    for entries in _entries_by_char.values():
        for entry in entries:
            token = entry.jyutping.split()[0]
            syl = _parse_syllable_token(token)
            if not syl or not syllable_matches_rhyme_fragment(syl.letters, letters):
                continue
            if is_standalone_nasal_syllable_token(token):
                finals |= set(STANDALONE_NASAL_FINALS)
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
    fragment = normalize_rhyme_letters(letters)
    if fragment == STANDALONE_NG:
        keys = rhyme_final_index_keys_per_position(get_word_jyutping(word) or "")
        if pos < len(keys) and keys[pos] & STANDALONE_NASAL_FINALS:
            return True
    options = rhyme_letter_final_options(letters)
    if not options:
        return False
    parts = get_rhyme_finals(word)
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
    jyut = get_word_jyutping(word)
    if is_standalone_nasal_syllable_token(syllable_token_at(jyut, pos)):
        return False
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
