"""查詢語意解釋 — ParsedQuery → MatchSpec → Explain IR → render (ADR-0021)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.lexicon.rhyme_match_profile import (
    RHYME_PROFILE_LABELS,
    normalize_rhyme_profile,
)
from app.services._generated.query_kind_registry import QueryKind
from app.services.ping_zak import slot_label
from app.services.query_parse import normalize_and_parse
from app.services.query_types import (
    DigitCodeQuery,
    HeteronymCodeQuery,
    JyutpingAnchorQuery,
    JyutpingFragmentQuery,
    ParsedQuery,
    PingZeSerialQuery,
    RelationLookupQuery,
    UnmatchedQuery,
    WordLookupQuery,
)

from app.services.query_explain_ir import (
    _build_match_spec,
    build_explain_ir,
    explain_ir_for_query,
)
from app.services.query_explain_render import _width_label, render_explain_ir

_FINAL_RHYME_KINDS = frozenset(
    {
        QueryKind.EQUALS,
        QueryKind.PREFIX_WILDCARD_EQUALS,
        QueryKind.PARTIAL_RHYME_MASK,
        QueryKind.SERIAL_PHONEME,
        QueryKind.RHYME_ANCHOR,
        QueryKind.TRIPLE_RHYME_ANCHOR,
        QueryKind.JYUTPING_ANCHOR,
        QueryKind.CODE_REF_MIDDLE_RHYME,
        QueryKind.COMPOUND_SYN,
        QueryKind.COMPOUND_ANT,
        QueryKind.COMPOUND_CONNECT_SYN,
        QueryKind.COMPOUND_CONNECT_ANT,
        QueryKind.COMPOUND_DOUBLED_SYLLABLE,
    }
)


@dataclass(frozen=True)
class QueryExplainResult:
    summary: Optional[str]
    warning: Optional[str]
    kind: Optional[str]


def _has_final_rhyme_constraint(parsed: ParsedQuery) -> bool:
    if parsed.kind in _FINAL_RHYME_KINDS:
        if parsed.kind == QueryKind.SERIAL_PHONEME:
            return getattr(parsed, "constraint", None) == "final"
        if parsed.kind == QueryKind.JYUTPING_ANCHOR:
            kind = getattr(parsed, "anchor_kind", None)
            return kind in ("rhyme_letters", "syllable_letters") or bool(
                getattr(parsed, "hybrid_rhyme", False)
            )
        if parsed.kind in (
            QueryKind.COMPOUND_SYN,
            QueryKind.COMPOUND_ANT,
            QueryKind.COMPOUND_CONNECT_SYN,
            QueryKind.COMPOUND_CONNECT_ANT,
            QueryKind.COMPOUND_DOUBLED_SYLLABLE,
        ):
            return bool(getattr(parsed, "rhyme_char", None))
        return True
    return bool(getattr(parsed, "rhyme_char", None))


def _append_rhyme_profile_label(summary: Optional[str], parsed: ParsedQuery, rhyme_profile: object) -> Optional[str]:
    """E1: 有同韻約束且非正韻時標明檔。"""
    if not summary or not _has_final_rhyme_constraint(parsed):
        return summary
    profile = normalize_rhyme_profile(rhyme_profile)
    if profile == "exact":
        return summary
    label = RHYME_PROFILE_LABELS.get(profile)
    if not label:
        return summary
    return f"{summary}（{label}）"


def explain_query(
    q: str,
    mode: str = "m1",
    pzmode: str | None = None,
    rhyme_profile: str | None = None,
) -> QueryExplainResult:
    text = (q or "").strip()
    if not text:
        return QueryExplainResult(None, None, None)
    parsed = normalize_and_parse(text, mode=mode, pzmode=pzmode)
    warning = _warning_for(parsed)
    if isinstance(parsed, UnmatchedQuery):
        return QueryExplainResult(None, parsed.hint or warning, parsed.kind.value)
    summary = _append_rhyme_profile_label(_summary_for(parsed), parsed, rhyme_profile)
    return QueryExplainResult(summary, warning, parsed.kind.value)


def _summary_for(parsed: ParsedQuery) -> Optional[str]:
    if isinstance(parsed, WordLookupQuery):
        return f"查詢詞條「{parsed.raw_q}」"
    if isinstance(parsed, DigitCodeQuery):
        return f"查同{parsed.raw_q}同音嘅字"
    if isinstance(parsed, PingZeSerialQuery):
        parts = [slot_label(ch) for ch in parsed.raw_q]
        return f"查{'、'.join(parts)}嘅{_width_label(len(parsed.raw_q))}詞"
    if isinstance(parsed, RelationLookupQuery):
        label = "近義詞" if parsed.relation_kind == "syn" else "反義詞"
        prefix = f"碼 {parsed.code_prefix} " if parsed.code_prefix else ""
        return f"查「{parsed.word}」嘅{prefix}{label}"
    if isinstance(parsed, JyutpingFragmentQuery):
        tone = "（有聲調）" if any(ch in "123456" for ch in parsed.raw_q) else "（不需聲調）"
        return f"粵拼查詢「{parsed.raw_q}」{tone}"
    if isinstance(parsed, HeteronymCodeQuery):
        return (
            f"查同字面異讀（{parsed.left_template}/{parsed.right_template}）："
            f"搵至少兩個唔同讀音，分別符合左右碼位模板"
        )
    if isinstance(parsed, UnmatchedQuery):
        return None

    spec = _build_match_spec(parsed)
    if spec is None:
        raw = getattr(parsed, "raw_q", None)
        return f"查詢「{raw}」" if raw else "查詢"
    return render_explain_ir(build_explain_ir(spec, parsed))


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


__all__ = [
    "QueryExplainResult",
    "build_explain_ir",
    "explain_ir_for_query",
    "explain_query",
    "render_explain_ir",
]
