"""查詢語意解釋 — ParsedQuery → MatchSpec → Explain IR → render (ADR-0021)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.services.position_match.spec import MatchSpec, get_equals_span
from app.services.query_parse import normalize_and_parse
from app.services.ping_zak import slot_label
from app.services.query_types import (
    CompoundDoubledSyllableQuery,
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


def build_explain_ir(spec: MatchSpec, parsed: ParsedQuery) -> dict[str, Any]:
    """MatchSpec path: structural IR (creator copy only in render)."""
    working = spec
    if spec.extra.get("dual_phoneme"):
        dual = spec.extra.get("dual_final_spec")
        if isinstance(dual, MatchSpec):
            working = dual

    from app.services.position_match.mask_adapter import has_code_digit_constraints

    equals = get_equals_span(working)
    if equals and has_code_digit_constraints(working):
        return _ir_code_sandwich(working, equals, parsed)
    if equals and working.extra.get("prefix_wildcard_equals"):
        return _ir_prefix_wildcard_equals(working, equals)
    if equals and equals.whole_word:
        return _ir_whole_word_equals(working, equals)
    if working.compound_kind:
        return _ir_compound(working)
    return _ir_slot_scan(working, equals)


def render_explain_ir(ir: dict[str, Any]) -> str:
    variant = ir["variant"]
    if variant == "whole_word_equals":
        return _render_whole_word_equals(ir)
    if variant == "prefix_wildcard_equals":
        return _render_prefix_wildcard_equals(ir)
    if variant == "code_sandwich_whole_word":
        return _render_code_sandwich_whole_word(ir)
    if variant == "code_sandwich_scan":
        return _render_code_sandwich_scan(ir)
    if variant == "compound":
        return _render_compound(ir)
    if variant == "slot_scan":
        return _render_slot_scan(ir)
    return _width_label(ir.get("width", 1))


def explain_ir_for_query(q: str, mode: str = "m1", pzmode: str | None = None) -> dict[str, Any] | None:
    """Parity helper: IR for MatchSpec-path queries only."""
    text = (q or "").strip()
    if not text:
        return None
    parsed = normalize_and_parse(text, mode=mode, pzmode=pzmode)
    if isinstance(parsed, UnmatchedQuery):
        return None
    if _is_short_circuit(parsed):
        return None
    spec = _build_match_spec(parsed)
    if spec is None:
        return None
    return build_explain_ir(spec, parsed)


def _is_short_circuit(parsed: ParsedQuery) -> bool:
    return isinstance(
        parsed,
        (
            WordLookupQuery,
            DigitCodeQuery,
            PingZeSerialQuery,
            RelationLookupQuery,
            JyutpingFragmentQuery,
            HeteronymCodeQuery,
        ),
    )


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


def _equals_ir(equals) -> dict[str, Any]:
    dim = "final" if equals.dimension == "final" else "initial"
    return {
        "dimension": dim,
        "ref_literal": equals.ref_literal,
        "whole_word": bool(equals.whole_word),
        "start_pos": equals.start_pos,
    }


def _code_prefix_ir(spec: MatchSpec) -> Optional[dict[str, Any]]:
    from app.services.position_match.mask_adapter import (
        code_digit_string_from_spec,
        required_codes_from_spec,
    )

    code = code_digit_string_from_spec(spec)
    if not code:
        return None
    required = required_codes_from_spec(spec)
    per_digit_full = (
        all(d is not None for d in required) and len(required) == spec.width
    )
    return {"digits": code, "per_digit_full": per_digit_full}


def _constraints_to_ir(constraints: dict[int, tuple[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pos, (kind, value) in sorted(constraints.items()):
        entry: dict[str, Any] = {"pos": pos, "kind": kind}
        if kind == "code_digit":
            entry["digit"] = value
        elif kind == "literal_char":
            entry["char"] = value
        elif kind == "wildcard":
            entry["symbol"] = value
        elif kind in ("final_anchor", "initial_anchor"):
            entry["ref"] = value
        elif kind in ("rhyme_letters", "initial_letters", "syllable_letters"):
            entry["letters"] = value
        elif kind in ("hybrid_tail_rhyme", "hybrid_tail_initial", "hybrid_code_literal"):
            digit, ref = value.split("|", 1)
            entry["digit"] = digit
            entry["ref"] = ref
        else:
            entry["ref"] = value
        items.append(entry)
    return items


def _ir_whole_word_equals(spec: MatchSpec, equals) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "variant": "whole_word_equals",
        "width": spec.width,
        "equals": _equals_ir(equals),
    }
    code_prefix = _code_prefix_ir(spec)
    if code_prefix:
        ir["code_prefix"] = code_prefix
    return ir


def _ir_prefix_wildcard_equals(spec: MatchSpec, equals) -> dict[str, Any]:
    return {
        "variant": "prefix_wildcard_equals",
        "width": spec.width,
        "equals": _equals_ir(equals),
    }


def _ir_code_sandwich(spec: MatchSpec, equals, parsed: ParsedQuery) -> dict[str, Any]:
    raw = getattr(parsed, "raw_q", "") or ""
    if equals.whole_word:
        ir: dict[str, Any] = {
            "variant": "code_sandwich_whole_word",
            "width": spec.width,
            "raw_q": raw,
            "equals": _equals_ir(equals),
        }
        code_prefix = _code_prefix_ir(spec)
        if code_prefix:
            ir["code_prefix"] = code_prefix
        return ir
    constraints = _effective_constraints(spec, equals)
    return {
        "variant": "code_sandwich_scan",
        "width": spec.width,
        "raw_q": raw,
        "constraints": _constraints_to_ir(constraints),
    }


def _ir_compound(spec: MatchSpec) -> dict[str, Any]:
    compound: dict[str, Any] = {
        "kind": spec.compound_kind,
        "width": spec.width,
    }
    if spec.compound_kind == "doubled_syllable":
        rhyme = next(
            (s.value for s in spec.slots if s.kind == "final_anchor" and isinstance(s.value, str)),
            None,
        )
        from app.services.position_match.mask_adapter import code_digit_string_from_spec

        code = code_digit_string_from_spec(spec)
        if code:
            compound["code"] = code
        if rhyme:
            compound["tail_rhyme"] = rhyme
    else:
        connective = spec.extra.get("connective")
        if connective:
            compound["connective"] = str(connective)
    return {"variant": "compound", "width": spec.width, "compound": compound}


def _ir_slot_scan(spec: MatchSpec, equals) -> dict[str, Any]:
    constraints = _effective_constraints(spec, equals)
    return {
        "variant": "slot_scan",
        "width": spec.width,
        "constraints": _constraints_to_ir(constraints),
    }


def _render_code_prefix_phrase(code_prefix: dict[str, Any]) -> str:
    digits = code_prefix["digits"]
    if code_prefix["per_digit_full"]:
        parts = [
            f"{_word_pos(i)}同 {digit} 同音"
            for i, digit in enumerate(digits)
        ]
        return "，".join(parts)
    return f"前 {len(digits)} 個字為碼 {digits}"


def _render_whole_word_equals(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    line = f"整詞同「{equals['ref_literal']}」{dim}（{label}）"
    code_prefix = ir.get("code_prefix")
    if code_prefix:
        return f"{line}；{_render_code_prefix_phrase(code_prefix)}"
    return line


def _render_prefix_wildcard_equals(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    positions = list(range(equals["start_pos"], ir["width"]))
    pos_label = _pos_list_label(positions)
    return (
        f"首個字任意；{pos_label}同「{equals['ref_literal']}」{dim}（{label}）"
    )


def _render_code_sandwich_whole_word(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    rhyme_line = f"同「{equals['ref_literal']}」{dim}（{label}）"
    code_prefix = ir.get("code_prefix")
    body = rhyme_line if not code_prefix else f"{rhyme_line}；{_render_code_prefix_phrase(code_prefix)}"
    return f"數字夾字「{ir['raw_q']}」：{body}"


def _render_constraint_phrase(c: dict[str, Any]) -> str:
    pos = c["pos"]
    kind = c["kind"]
    label = _word_pos(pos)
    if kind == "code_digit":
        return f"{label}同 {c['digit']} 同音"
    if kind == "literal_char":
        return f"{label}為「{c['char']}」"
    if kind == "wildcard":
        return f"{label}任意字"
    if kind == "hybrid_tail_rhyme":
        return f"{label}同 {c['digit']} 同音且同「{c['ref']}」同韻"
    if kind == "hybrid_tail_initial":
        return f"{label}同 {c['digit']} 同音且同「{c['ref']}」同聲"
    if kind == "hybrid_code_literal":
        return f"{label}同 {c['digit']} 同音且限定為{c['ref']}"
    if kind == "final_anchor":
        return f"{label}同「{c['ref']}」同韻"
    if kind == "initial_anchor":
        return f"{label}同「{c['ref']}」同聲"
    if kind == "rhyme_letters":
        return f"{label}同韻母 {c['letters']}"
    if kind == "initial_letters":
        return f"{label}同聲母 {c['letters']}"
    if kind == "syllable_letters":
        return f"{label}粵拼音節 {c['letters']}"
    ref = c.get("ref", "")
    return f"{label}為「{ref}」"


def _render_constraints(constraints: list[dict[str, Any]]) -> str:
    return "，".join(_render_constraint_phrase(c) for c in constraints)


def _render_code_sandwich_scan(ir: dict[str, Any]) -> str:
    constraints = ir.get("constraints") or []
    if constraints:
        return f"數字夾字「{ir['raw_q']}」：{_render_constraints(constraints)}"
    return f"數字夾字「{ir['raw_q']}」"


def _render_compound(ir: dict[str, Any]) -> str:
    compound = ir["compound"]
    if compound["kind"] == "doubled_syllable":
        n = compound["width"]
        code = compound.get("code")
        rhyme = compound.get("tail_rhyme")
        base = f"查{n}字雙聲疊韻字（各字音節相同，聲調不限）"
        if code and rhyme:
            return f"查{n}字雙聲疊韻字（碼 {code}，尾字同「{rhyme}」同韻）"
        if code:
            return f"查{n}字雙聲疊韻字（碼 {code}）"
        if rhyme:
            return f"查{n}字雙聲疊韻字（尾字同「{rhyme}」同韻）"
        return base
    label = "近義" if compound["kind"] == "syn" else "反義"
    connective = compound.get("connective")
    if connective:
        return f"查詢含「{connective}」嘅{label}複合詞"
    return f"查詢{label}複合詞"


def _render_slot_scan(ir: dict[str, Any]) -> str:
    constraints = ir.get("constraints") or []
    if not constraints:
        return _width_label(ir["width"])
    return f"{_width_label(ir['width'])}：{_render_constraints(constraints)}"


def _effective_constraints(
    spec: MatchSpec,
    equals,
) -> dict[int, tuple[str, str]]:
    from app.services.position_match.mask_adapter import required_codes_from_spec

    result: dict[int, tuple[str, str]] = {}
    required = required_codes_from_spec(spec)
    for i, digit in enumerate(required):
        if digit is not None:
            result.setdefault(i, ("code_digit", str(digit)))

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
        value = str(value)
        existing = result.get(slot.pos)
        if slot.kind == "final_anchor" and existing and existing[0] == "code_digit":
            result[slot.pos] = ("hybrid_tail_rhyme", f"{existing[1]}|{value}")
            continue
        if slot.kind == "initial_anchor" and existing and existing[0] == "code_digit":
            result[slot.pos] = ("hybrid_tail_initial", f"{existing[1]}|{value}")
            continue
        if slot.kind == "literal_char" and existing and existing[0] == "code_digit":
            result[slot.pos] = ("hybrid_code_literal", f"{existing[1]}|{value}")
            continue
        if existing and _SLOT_PRIORITY.get(existing[0], 0) >= _SLOT_PRIORITY.get(
            slot.kind, 0
        ):
            continue
        result[slot.pos] = (slot.kind, value)

    if equals and not equals.whole_word:
        dim_kind = (
            "final_anchor" if equals.dimension == "final" else "initial_anchor"
        )
        for i, ch in enumerate(equals.ref_literal):
            pos = equals.start_pos + i
            if 0 <= pos < spec.width:
                digit = required[pos] if pos < len(required) else None
                if digit is not None and equals.dimension == "final" and not equals.phoneme_anchor_only:
                    result[pos] = ("hybrid_tail_rhyme", f"{digit}|{ch}")
                elif equals.phoneme_anchor_only and digit is not None:
                    kind = (
                        "hybrid_tail_rhyme"
                        if equals.dimension == "final"
                        else "hybrid_tail_initial"
                    )
                    result[pos] = (kind, f"{digit}|{ch}")
                else:
                    result[pos] = (dim_kind, ch)

    return result


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
