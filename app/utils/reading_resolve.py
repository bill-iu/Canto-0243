"""維護用：為音節槽與 CJK 字數不符的詞條解析完整粵拼（rime／詞級標音／pycantonese）。"""

from __future__ import annotations

import json
import re
from typing import Optional

from app.domain.lexicon.admission import resolve_admission
from app.lexicon.static_index import LexiconEntry
from app.utils.jyutping_codec import get_0243_code, split_jyutping

_CJK = re.compile(r"[\u4e00-\u9fff]")


def cjk_literal(text: str) -> str:
    return "".join(_CJK.findall(text or ""))


def phoneme_slot_count(jyutping: str) -> int:
    if not (jyutping or "").strip():
        return 0
    _, finals_json, _ = split_jyutping(jyutping)
    try:
        finals = json.loads(finals_json)
        return len(finals) if isinstance(finals, list) else 0
    except (TypeError, json.JSONDecodeError):
        return 0


def _entry_if_slots_match(literal: str, jyutping: str, code: str, target: int) -> Optional[LexiconEntry]:
    if phoneme_slot_count(jyutping) != target:
        return None
    return LexiconEntry(char=literal, jyutping=jyutping.strip(), code=code or get_0243_code(jyutping) or "")


def _jyutping_from_pycantonese(cjk: str) -> Optional[str]:
    import pycantonese

    try:
        pairs = pycantonese.characters_to_jyutping(cjk)
    except Exception:
        return None
    if not pairs:
        return None
    if len(pairs) == 1 and pairs[0][0] == cjk:
        jp = pairs[0][1]
        return jp.strip() if jp else None

    syllables: list[str] = []
    for ch in cjk:
        try:
            cp = pycantonese.characters_to_jyutping(ch)
        except Exception:
            return None
        if not cp or not cp[0][1]:
            return None
        syllables.extend(cp[0][1].split())
    if len(syllables) != len(cjk):
        return None
    return " ".join(syllables)


def resolve_repair_reading(literal: str) -> Optional[LexiconEntry]:
    """音節槽須對齊 CJK 字數（標點唔計槽）；None = 無法自動修復。"""
    text = (literal or "").strip()
    cjk = cjk_literal(text)
    if not cjk:
        return None
    target = len(cjk)

    admission = resolve_admission(text)
    for ent in admission.entries:
        fixed = _entry_if_slots_match(text, ent.jyutping, ent.code, target)
        if fixed:
            return fixed

    if cjk != text:
        admission_cjk = resolve_admission(cjk)
        for ent in admission_cjk.entries:
            fixed = _entry_if_slots_match(text, ent.jyutping, ent.code, target)
            if fixed:
                return fixed

    jyut = _jyutping_from_pycantonese(cjk)
    if not jyut:
        return None
    return _entry_if_slots_match(text, jyut, "", target)


__all__ = [
    "cjk_literal",
    "phoneme_slot_count",
    "resolve_repair_reading",
]
