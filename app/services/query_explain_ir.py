"""Explain IR build — MatchSpec → structural IR (ADR-0021)."""
from __future__ import annotations

import re
from typing import Any, Optional

from app.services.position_match.canonical import CanonicalMatchSpec
from app.services.position_match.compiler import compile_parsed_query
from app.services.query_parse import normalize_and_parse
from app.services.query_types import (
    DigitCodeQuery,
    HeteronymCodeQuery,
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


def build_explain_ir(spec: CanonicalMatchSpec, parsed: ParsedQuery) -> dict[str, Any]:
    """MatchSpec path: structural IR (creator copy only in render)."""
    working = spec.phoneme_alternatives.final if spec.phoneme_alternatives else spec

    from app.services.position_match.mask_adapter import has_code_digit_constraints

    equals = working.equals_span
    if equals and has_code_digit_constraints(working):
        return _ir_code_sandwich(working, equals, parsed)
    if equals and equals.start_pos == 1 and equals.phoneme_anchor_only:
        return _ir_prefix_wildcard_equals(working, equals)
    if equals and equals.whole_word:
        return _ir_whole_word_equals(working, equals)
    if working.compound:
        return _ir_compound(working)
    return _ir_slot_scan(working, equals)


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
    spec = compile_parsed_query(parsed)
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


def _build_match_spec(parsed: ParsedQuery) -> Optional[CanonicalMatchSpec]:
    return compile_parsed_query(parsed)


def _equals_ir(equals) -> dict[str, Any]:
    dim = "final" if equals.dimension == "final" else "initial"
    return {
        "dimension": dim,
        "ref_literal": equals.ref_literal,
        "whole_word": bool(equals.whole_word),
        "start_pos": equals.start_pos,
    }


def _code_prefix_ir(spec: CanonicalMatchSpec) -> Optional[dict[str, Any]]:
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


def _ir_whole_word_equals(spec: CanonicalMatchSpec, equals) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "variant": "whole_word_equals",
        "width": spec.width,
        "equals": _equals_ir(equals),
    }
    code_prefix = _code_prefix_ir(spec)
    if code_prefix:
        ir["code_prefix"] = code_prefix
    return ir


def _ir_prefix_wildcard_equals(spec: CanonicalMatchSpec, equals) -> dict[str, Any]:
    return {
        "variant": "prefix_wildcard_equals",
        "width": spec.width,
        "equals": _equals_ir(equals),
    }


def _ir_code_sandwich(spec: CanonicalMatchSpec, equals, parsed: ParsedQuery) -> dict[str, Any]:
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


def _ir_compound(spec: CanonicalMatchSpec) -> dict[str, Any]:
    compound: dict[str, Any] = {
        "kind": spec.compound.kind,
        "width": spec.width,
    }
    if spec.compound.kind == "doubled_syllable":
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
        connective = spec.compound.connective
        if connective:
            compound["connective"] = str(connective)
    return {"variant": "compound", "width": spec.width, "compound": compound}


def _ir_slot_scan(spec: CanonicalMatchSpec, equals) -> dict[str, Any]:
    constraints = _effective_constraints(spec, equals)
    return {
        "variant": "slot_scan",
        "width": spec.width,
        "constraints": _constraints_to_ir(constraints),
    }


def _effective_constraints(
    spec: CanonicalMatchSpec,
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
