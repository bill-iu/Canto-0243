"""查詢語意解釋 — ParsedQuery → MatchSpec → Explain IR → render (ADR-0021)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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


@dataclass(frozen=True)
class QueryExplainResult:
    summary: Optional[str]
    warning: Optional[str]
    kind: Optional[str]


def explain_query(q: str, mode: str = "m1", pzmode: str | None = None) -> QueryExplainResult:
    text = (q or "").strip()
    if not text:
        return QueryExplainResult(None, None, None)
    parsed = normalize_and_parse(text, mode=mode, pzmode=pzmode)
    warning = _warning_for(parsed)
    if isinstance(parsed, UnmatchedQuery):
        return QueryExplainResult(None, parsed.hint or warning, parsed.kind.value)
    summary = _summary_for(parsed)
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
