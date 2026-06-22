"""查詢語意解釋 — ParsedQuery → MatchSpec slot scan → creator-facing copy (ADR-0021)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.services.position_match.spec import MatchSpec, get_equals_span
from app.services.query_parse import normalize_and_parse
from app.services.query_types import (
    DigitCodeQuery,
    HybridTailEqualsAliasQuery,
    JyutpingAnchorQuery,
    JyutpingFragmentQuery,
    ParsedQuery,
    RelationLookupQuery,
    UnmatchedQuery,
    WordLookupQuery,
)

_WILDCARD_RE = re.compile(r"^[?_%]$")
_DIGIT_RE = re.compile(r"^\d$")
_CANTO_RE = re.compile(r"^[一-龥]$")
_CN_WIDTH = ("", "一", "兩", "三", "四", "五", "六", "七", "八", "九", "十")
_RHYME_LABELS = ("", "單押", "雙押", "三押", "四押")
_SLOT_PRIORITY = {
    "wildcard": 0,
    "code_digit": 1,
    "literal_char": 2,
    "final_anchor": 3,
    "initial_anchor": 3,
    "rhyme_letters": 4,
    "initial_letters": 4,
    "syllable_letters": 4,
}


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


def _rhyme_label(n: int) -> str:
    if n < len(_RHYME_LABELS):
        return _RHYME_LABELS[n]
    return f"{n}押"


def _rhyme_or_initial(dimension: str) -> str:
    return "同韻" if dimension == "final" else "同聲"


def _pos_list_label(positions: list[int]) -> str:
    if len(positions) == 1:
        return _word_pos(positions[0])
    nums = "、".join(f"第 {p + 1}" for p in positions)
    return f"{nums} 個字"


def _build_match_spec(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_match_spec_registry import build_match_spec_for_parsed

    return build_match_spec_for_parsed(parsed)


def _summary_for(parsed: ParsedQuery) -> Optional[str]:
    if isinstance(parsed, WordLookupQuery):
        return f"查詢詞條「{parsed.raw_q}」"
    if isinstance(parsed, DigitCodeQuery):
        return f"查同{parsed.raw_q}同音嘅字"
    if isinstance(parsed, RelationLookupQuery):
        label = "近義詞" if parsed.relation_kind == "syn" else "反義詞"
        prefix = f"碼 {parsed.code_prefix} " if parsed.code_prefix else ""
        return f"查「{parsed.word}」嘅{prefix}{label}"
    if isinstance(parsed, JyutpingFragmentQuery):
        return f"粵拼查詢「{parsed.raw_q}」"
    if isinstance(parsed, HybridTailEqualsAliasQuery):
        return f"碼夾等號查詢「{parsed.raw_q}」"
    if isinstance(parsed, UnmatchedQuery):
        return None

    spec = _build_match_spec(parsed)
    if spec is None:
        raw = getattr(parsed, "raw_q", None)
        return f"查詢「{raw}」" if raw else "查詢"
    return _summary_from_match_spec(spec, parsed)


def _summary_from_match_spec(spec: MatchSpec, parsed: ParsedQuery) -> Optional[str]:
    if spec.extra.get("dual_phoneme"):
        dual = spec.extra.get("dual_final_spec")
        if isinstance(dual, MatchSpec):
            spec = dual

    if spec.hybrid_ref_chars and len(spec.hybrid_ref_chars) > 1:
        return _hybrid_multi_char_summary(spec)

    equals = get_equals_span(spec)
    if equals and spec.extra.get("prefix_wildcard_equals"):
        return _prefix_wildcard_equals_summary(spec, equals)
    if equals and equals.whole_word:
        return _whole_word_equals_summary(spec, equals)

    if spec.compound_kind:
        return _compound_summary(spec)

    return _slot_scan_summary(spec, equals)


def _whole_word_equals_summary(spec: MatchSpec, equals) -> str:
    dim = _rhyme_or_initial(equals.dimension)
    label = _rhyme_label(len(equals.ref_literal))
    line = f"整詞同「{equals.ref_literal}」{dim}（{label}）"
    code_phrase = _code_prefix_phrase(spec)
    return f"{line}；{code_phrase}" if code_phrase else line


def _prefix_wildcard_equals_summary(spec: MatchSpec, equals) -> str:
    dim = _rhyme_or_initial(equals.dimension)
    label = _rhyme_label(len(equals.ref_literal))
    positions = list(range(equals.start_pos, spec.width))
    pos_label = _pos_list_label(positions)
    return (
        f"首個字任意；{pos_label}同「{equals.ref_literal}」{dim}（{label}）"
    )


def _hybrid_multi_char_summary(spec: MatchSpec) -> str:
    ref = spec.hybrid_ref_chars or ""
    parts = [_width_label(spec.width)]
    scan = _slot_scan_details(spec, None)
    if scan:
        parts.append(scan)
    parts.append(f"字面含「{ref}」")
    return "：".join(parts[:2]) + ("，" + "，".join(parts[2:]) if len(parts) > 2 else "")


def _compound_summary(spec: MatchSpec) -> str:
    label = "近義" if spec.compound_kind == "syn" else "反義"
    connective = spec.extra.get("connective")
    if connective:
        return f"查詢含「{connective}」嘅{label}複合詞"
    return f"查詢{label}複合詞"


def _code_prefix_phrase(spec: MatchSpec) -> Optional[str]:
    if not spec.code_prefix:
        return None
    if spec.width == len(spec.code_prefix):
        parts = [
            f"{_word_pos(i)}同 {digit} 同音"
            for i, digit in enumerate(spec.code_prefix)
        ]
        return "，".join(parts)
    return f"前 {len(spec.code_prefix)} 個字為碼 {spec.code_prefix}"


def _slot_scan_summary(spec: MatchSpec, equals) -> str:
    details = _slot_scan_details(spec, equals)
    if not details:
        return _width_label(spec.width)
    return f"{_width_label(spec.width)}：{details}"


def _slot_scan_details(spec: MatchSpec, equals) -> str:
    constraints = _effective_constraints(spec, equals)
    phrases = [
        _constraint_phrase(pos, kind, value)
        for pos, (kind, value) in sorted(constraints.items())
    ]
    return "，".join(phrases)


def _effective_constraints(
    spec: MatchSpec,
    equals,
) -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}

    if spec.code_prefix and spec.width == len(spec.code_prefix):
        for i, digit in enumerate(spec.code_prefix):
            result.setdefault(i, ("code_digit", digit))

    if spec.mask:
        for i, ch in enumerate(spec.mask):
            if i >= spec.width:
                break
            if _WILDCARD_RE.match(ch):
                result.setdefault(i, ("wildcard", ch))
            elif _DIGIT_RE.match(ch):
                result.setdefault(i, ("code_digit", ch))
            elif _CANTO_RE.match(ch):
                result.setdefault(i, ("literal_char", ch))

    for slot in spec.slots:
        value = slot.value if slot.value is not None else ""
        if isinstance(value, set):
            value = next(iter(value), "")
        existing = result.get(slot.pos)
        if existing and _SLOT_PRIORITY.get(existing[0], 0) >= _SLOT_PRIORITY.get(
            slot.kind, 0
        ):
            continue
        result[slot.pos] = (slot.kind, str(value))

    if equals and not equals.whole_word:
        dim_kind = (
            "final_anchor" if equals.dimension == "final" else "initial_anchor"
        )
        for i, ch in enumerate(equals.ref_literal):
            pos = equals.start_pos + i
            if 0 <= pos < spec.width:
                result[pos] = (dim_kind, ch)

    if spec.hybrid_ref_chars and len(spec.hybrid_ref_chars) == 1:
        pos = spec.hybrid_ref_pos if spec.hybrid_ref_pos is not None else 0
        result[pos] = ("final_anchor", spec.hybrid_ref_chars)

    return result


def _constraint_phrase(pos: int, kind: str, value: str) -> str:
    label = _word_pos(pos)
    if kind == "code_digit":
        return f"{label}同 {value} 同音"
    if kind == "literal_char":
        return f"{label}為「{value}」"
    if kind == "wildcard":
        return f"{label}任意字"
    if kind == "final_anchor":
        return f"{label}同「{value}」同韻"
    if kind == "initial_anchor":
        return f"{label}同「{value}」同聲"
    if kind == "rhyme_letters":
        return f"{label}同韻母 {value}"
    if kind == "initial_letters":
        return f"{label}同聲母 {value}"
    if kind == "syllable_letters":
        return f"{label}粵拼音節 {value}"
    return f"{label}為「{value}」"


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