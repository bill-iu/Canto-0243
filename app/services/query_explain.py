"""查詢語意解釋 — ParsedQuery → creator-facing copy (ADR-0021)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.services.query_parse import normalize_and_parse
from app.services.query_types import (
    HYBRID_CODE_RE,
    CompoundAntQuery,
    CompoundConnectAntQuery,
    CompoundConnectSynQuery,
    CompoundSynQuery,
    DigitCodeQuery,
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    JyutpingAnchorQuery,
    JyutpingFragmentQuery,
    LiteralRefQuery,
    MaskQuery,
    ParsedQuery,
    PlusAnchorQuery,
    PrefixWildcardEqualsQuery,
    RelationLookupQuery,
    RhymeAnchorQuery,
    SerialPhonemeAnchorQuery,
    UnmatchedQuery,
    WordLookupQuery,
)

_WILDCARD_RE = re.compile(r"^[?_%]$")
_DIGIT_RE = re.compile(r"^\d$")
_CANTO_RE = re.compile(r"^[一-龥]$")
_CN_WIDTH = ("", "一", "兩", "三", "四", "五", "六", "七", "八", "九", "十")


@dataclass(frozen=True)
class QueryExplainResult:
    summary: Optional[str]
    warning: Optional[str]
    kind: Optional[str]


def explain_query(q: str, mode: str = "m1") -> QueryExplainResult:
    del mode  # ponytail: reserved for mode-specific copy; parse is mode-agnostic today
    text = (q or "").strip()
    if not text:
        return QueryExplainResult(None, None, None)
    parsed = normalize_and_parse(text)
    warning = _warning_for(parsed)
    if isinstance(parsed, UnmatchedQuery):
        return QueryExplainResult(None, parsed.hint or warning, parsed.kind.value)
    summary = _summary_for(parsed)
    return QueryExplainResult(summary, warning, parsed.kind.value)


def _word_pos(n: int) -> str:
    return f"第 {n + 1} 個字"


def _width_label(width: int) -> str:
    cn = _CN_WIDTH[width] if width < len(_CN_WIDTH) else str(width)
    return f"{cn}個字"


def _rhyme_or_initial(constraint: str) -> str:
    return "同韻" if constraint == "final" else "同聲"


def _code_slots_phrase(code_slots: list[tuple[int, str]], width: int) -> Optional[str]:
    if not code_slots:
        return None
    positions = sorted(pos for pos, _ in code_slots)
    if positions == list(range(len(positions))) and len(positions) == width - 1:
        digits = "".join(d for _, d in sorted(code_slots, key=lambda x: x[0]))
        return f"前 {len(positions)} 個字為碼 {digits}"
    parts = [f"{_word_pos(pos)}為碼 {digit}" for pos, digit in sorted(code_slots, key=lambda x: x[0])]
    return "，".join(parts)


def _summary_for(parsed: ParsedQuery) -> Optional[str]:
    if isinstance(parsed, PlusAnchorQuery):
        return _plus_summary(parsed)
    if isinstance(parsed, RhymeAnchorQuery):
        return _rhyme_summary(parsed)
    if isinstance(parsed, MaskQuery):
        return _mask_summary(parsed.raw_q)
    if isinstance(parsed, JyutpingAnchorQuery):
        return _jyutping_summary(parsed)
    if isinstance(parsed, SerialPhonemeAnchorQuery):
        return _serial_summary(parsed)
    if isinstance(parsed, WordLookupQuery):
        return f"查詢詞條「{parsed.raw_q}」"
    if isinstance(parsed, DigitCodeQuery):
        return f"查詢 0243 碼「{parsed.raw_q}」"
    if isinstance(parsed, HybridCodeQuery):
        return _hybrid_code_summary(parsed.raw_q)
    if isinstance(parsed, LiteralRefQuery):
        pos = _word_pos(parsed.width - 1)
        return f"{_width_label(parsed.width)}：{pos}字面為「{parsed.literal_char}」，碼為 {parsed.code_digits}"
    if isinstance(parsed, RelationLookupQuery):
        label = "近義" if parsed.relation_kind == "syn" else "反義"
        prefix = f"碼 {parsed.code_prefix} " if parsed.code_prefix else ""
        return f"查詢「{parsed.word}」嘅{prefix}{label}關係"
    if isinstance(parsed, (CompoundSynQuery, CompoundAntQuery)):
        label = "近義" if isinstance(parsed, CompoundSynQuery) else "反義"
        return f"查詢{label}複合詞"
    if isinstance(parsed, (CompoundConnectSynQuery, CompoundConnectAntQuery)):
        label = "近義" if isinstance(parsed, CompoundConnectSynQuery) else "反義"
        return f"查詢含「{parsed.connective}」嘅{label}複合詞"
    if isinstance(parsed, EqualsQuery):
        return _equals_summary(parsed.raw_q)
    if isinstance(parsed, PrefixWildcardEqualsQuery):
        dim = "同韻" if parsed.raw_q.endswith("=") else "同聲"
        return f"{_width_label(parsed.width)}：首個字任意，其餘同「{parsed.ref_literal}」{dim}"
    if isinstance(parsed, JyutpingFragmentQuery):
        return f"粵拼查詢「{parsed.raw_q}」"
    if isinstance(parsed, HybridTailEqualsAliasQuery):
        return f"碼夾等號查詢「{parsed.raw_q}」"
    if isinstance(parsed, UnmatchedQuery):
        return None
    raw = getattr(parsed, "raw_q", None)
    return f"查詢「{raw}」" if raw else "查詢"


def _plus_summary(parsed: PlusAnchorQuery) -> str:
    parts = [_width_label(parsed.width)]
    code_phrase = _code_slots_phrase(parsed.code_slots, parsed.width)
    if code_phrase:
        parts.append(code_phrase)
    pos = _word_pos(parsed.anchor_pos)
    if parsed.constraint == "literal":
        parts.append(f"{pos}為「{parsed.anchor}」")
    else:
        parts.append(f"{pos}同「{parsed.anchor}」{_rhyme_or_initial(parsed.constraint)}")
    return "：".join(parts[:2]) + ("，" + "，".join(parts[2:]) if len(parts) > 2 else "")


def _rhyme_summary(parsed: RhymeAnchorQuery) -> str:
    pos = _word_pos(parsed.anchor_pos)
    dim = _rhyme_or_initial(parsed.constraint)
    if parsed.width == 1:
        return f"一個字：同「{parsed.anchor}」{dim}"
    parts = [_width_label(parsed.width), f"{pos}同「{parsed.anchor}」{dim}"]
    return "：".join(parts)


def _mask_summary(mask: str) -> str:
    width = len(mask)
    parts = [_width_label(width)]
    details: list[str] = []
    wildcard_positions: list[int] = []
    for idx, ch in enumerate(mask):
        if _WILDCARD_RE.match(ch):
            wildcard_positions.append(idx)
        elif _DIGIT_RE.match(ch):
            details.append(f"{_word_pos(idx)}為碼 {ch}")
        elif _CANTO_RE.match(ch):
            details.append(f"{_word_pos(idx)}為「{ch}」")
    if wildcard_positions:
        if len(wildcard_positions) == 1:
            details.append(f"{_word_pos(wildcard_positions[0])}為任意字")
        else:
            labels = "、".join(_word_pos(i) for i in wildcard_positions)
            details.append(f"{labels}為任意字")
    return "：".join([parts[0], "，".join(details)])


def _jyutping_summary(parsed: JyutpingAnchorQuery) -> str:
    parts = [_width_label(parsed.width)]
    if parsed.code_prefix:
        n = len(parsed.code_prefix)
        if n < parsed.width:
            parts.append(f"前 {n} 個字為碼 {parsed.code_prefix}")
    pos = _word_pos(parsed.anchor_pos)
    if parsed.anchor_kind == "rhyme_letters":
        parts.append(f"{pos}同韻母 {parsed.anchor_value}")
    elif parsed.anchor_kind == "initial_letters":
        parts.append(f"{pos}同聲母 {parsed.anchor_value}")
    else:
        parts.append(f"{pos}粵拼音節 {parsed.anchor_value}")
    return "：".join(parts[:2]) + ("，" + "，".join(parts[2:]) if len(parts) > 2 else "")


def _serial_summary(parsed: SerialPhonemeAnchorQuery) -> str:
    dim = _rhyme_or_initial(parsed.constraint)
    anchor_bits = [
        f"{_word_pos(pos)}同「{char}」{dim}"
        for pos, char in parsed.anchors
    ]
    return f"{_width_label(parsed.width)}：串列錨——" + "，".join(anchor_bits)


def _hybrid_code_summary(raw_q: str) -> str:
    match = HYBRID_CODE_RE.match(raw_q)
    if not match:
        return f"碼字查詢「{raw_q}」"
    digits = match.group(1)
    ref = match.group(2)
    width = len(digits)
    if len(ref) == 1:
        return f"{_width_label(width)}：碼 {digits}，{_word_pos(width - 1)}同「{ref}」同韻"
    return f"{_width_label(width)}：碼 {digits}，字面含「{ref}」"


def _equals_summary(raw_q: str) -> str:
    inner = raw_q.strip()
    if inner.startswith("="):
        return f"整詞同「{inner[1:]}」同聲"
    if inner.endswith("="):
        return f"整詞同「{inner[:-1]}」同韻"
    return f"等號查詢「{inner}」"


def _warning_for(parsed: ParsedQuery) -> Optional[str]:
    if not isinstance(parsed, JyutpingAnchorQuery):
        return None
    if not parsed.hybrid_rhyme or parsed.anchor_kind != "rhyme_letters":
        return None
    value = parsed.anchor_value
    prefix = parsed.code_prefix or ""
    if parsed.width == 2 and "+" not in parsed.raw_q:
        return f"易混：三個字請改「{prefix}+{value}」"
    if parsed.width >= 3 and "+" in parsed.raw_q:
        return f"易混：兩個字請改「{prefix}{value}」"
    return None


__all__ = ["QueryExplainResult", "explain_query"]