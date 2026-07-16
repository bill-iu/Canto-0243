"""粵拼錨：缺字家族內拉丁錨解析與分類（CONTEXT § 粵拼錨）。"""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from app.services.jyutping_match import _parse_syllable_token
from app.services.query_tokens import CODE_TAIL_MIDDLE

_SLOT = re.escape(CODE_TAIL_MIDDLE)

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
    if text in ("gw", "kw"):
        return "initial_letters"
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


def _is_hybrid_initial_letters(letters: str) -> bool:
    """碼尾／中格聲母：單輔音或 gw／kw；ng／m 走 dual／韻，唔入呢條。"""
    text = (letters or "").strip().lower()
    if text in ("gw", "kw"):
        return True
    if text in AMBIGUOUS_PHONEME_LETTERS or text in VOWEL_RHYME_LETTERS:
        return False
    return len(text) == 1 and classify_latin_anchor(text) == "initial_letters"


def _dense_code_slots(prefix: str) -> list[tuple[int, str]]:
    return [(i, d) for i, d in enumerate(prefix)]


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
    """`$`+單漢字 → 拉丁完整音節字母；保留連續 `$` 供雙聲疊韻字查詢。"""
    if not q or "$" not in q:
        return q
    out: list[str] = []
    i = 0
    while i < len(q):
        if q[i] == "$":
            j = i
            while j < len(q) and q[j] == "$":
                j += 1
            if j - i >= 2:
                out.append(q[i:j])
                i = j
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
        prefix = left + right
        return {
            "raw_q": q,
            "width": len(prefix),
            "anchor_pos": max(0, len(left) - 1),
            "anchor_kind": "rhyme_letters",
            "anchor_value": normalize_rhyme_letters(letters),
            "code_prefix": prefix,
            "code_slots": _dense_code_slots(prefix),
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
    prefix = m.group(1) + m.group(3)
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "initial_letters",
        "anchor_value": cluster,
        "code_prefix": prefix,
        "code_slots": _dense_code_slots(prefix),
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
    prefix = m.group(1) + m.group(3)
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "syllable_letters",
        "anchor_value": letters,
        "code_prefix": prefix,
        "code_slots": _dense_code_slots(prefix),
    }


def parse_code_initial_query(q: str) -> Optional[dict]:
    """{首碼}{輔音}{末碼} — 聲母錨（3h4）。"""
    m = re.match(r"^(\d)([a-z])(\d)$", q)
    if not m:
        return None
    letter = m.group(2).lower()
    if classify_latin_anchor(letter) != "initial_letters":
        return None
    prefix = m.group(1) + m.group(3)
    return {
        "raw_q": q,
        "width": 2,
        "anchor_pos": 0,
        "anchor_kind": "initial_letters",
        "anchor_value": letter,
        "code_prefix": prefix,
        "code_slots": _dense_code_slots(prefix),
        "equals_style": True,
    }


def parse_code_initial_three_query(q: str) -> Optional[dict]:
    """{首碼}+{聲母}{末碼} / {首碼}?{聲母}{末碼} — 三字中格聲母（3+p4 ≡ 3?p4；gw／kw 同）。"""
    m = re.match(rf"^(\d)[\?{_SLOT}]([a-zA-Z]+)(\d)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if not _is_hybrid_initial_letters(letters):
        return None
    return {
        "raw_q": q,
        "width": 3,
        "anchor_pos": 1,
        "anchor_kind": "initial_letters",
        "anchor_value": letters,
        "code_prefix": m.group(1) + m.group(3),
        "code_slots": [(0, m.group(1)), (2, m.group(3))],
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
    prefix = left + right
    width = len(prefix)
    return {
        "raw_q": q,
        "width": width,
        "anchor_pos": max(0, len(left) - 1),
        "anchor_kind": "rhyme_letters",
        "anchor_value": normalize_rhyme_letters(letters),
        "code_prefix": prefix,
        "code_slots": _dense_code_slots(prefix),
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
        "code_slots": _dense_code_slots(prefix),
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
        "code_slots": _dense_code_slots(prefix),
        "hybrid_rhyme": True,
    }


def parse_hybrid_initial_query(q: str) -> Optional[dict]:
    """{碼}{聲母} — 碼後聲母錨末格（34p／34gw，對 23o）。"""
    m = re.match(r"^(\d+)([a-zA-Z]+)$", q)
    if not m or "?" in q or CODE_TAIL_MIDDLE in q:
        return None
    letters = m.group(2).lower()
    if not _is_hybrid_initial_letters(letters):
        return None
    prefix = m.group(1)
    return {
        "raw_q": q,
        "width": len(prefix),
        "anchor_pos": len(prefix) - 1,
        "anchor_kind": "initial_letters",
        "anchor_value": letters,
        "code_prefix": prefix,
        "code_slots": _dense_code_slots(prefix),
        "equals_style": True,
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
        "code_slots": _dense_code_slots(code),
        "hybrid_rhyme": True,
    }


def parse_code_initial_plus_tail_query(q: str) -> Optional[dict]:
    """{碼}+{聲母} — 三字碼尾聲母錨（34+p／34+gw，對 23+o）。"""
    m = re.match(rf"^(\d+){_SLOT}([a-zA-Z]+)$", q)
    if not m:
        return None
    letters = m.group(2).lower()
    if not _is_hybrid_initial_letters(letters):
        return None
    code = m.group(1)
    return {
        "raw_q": q,
        "width": len(code) + 1,
        "anchor_pos": len(code),
        "anchor_kind": "initial_letters",
        "anchor_value": letters,
        "code_prefix": code,
        "code_slots": _dense_code_slots(code),
        "equals_style": True,
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
        parse_code_initial_three_query,
        parse_code_cluster_initial_query,
        parse_code_initial_query,
        parse_code_syllable_two_query,
        parse_code_rhyme_equals_query,
        parse_code_rhyme_plus_tail_query,
        parse_code_initial_plus_tail_query,
        parse_hybrid_jyutping_syllable_query,
        parse_rhyme_vowel_hybrid_query,
        parse_hybrid_initial_query,
    ):
        parsed = parser(q)
        if parsed:
            return parsed
    return None


def is_jyutping_anchor_mask_query(q: str) -> bool:
    return parse_jyutping_anchor_query(q) is not None
