"""Canonical immutable MatchSpec value seam.

The migration adapter in this module lets existing callers move one seam at a
time. It has no database knowledge; execution adapters choose their physical
candidate plan after receiving the semantic value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

from app.services.position_match.spec import EqualsSpan, MatchSpec, SlotConstraint, get_equals_span

CanonicalSlotValue = Union[str, tuple[str, ...]]
CandidateScope = Literal["bounded", "complete"]
RankingPolicy = Literal["default", "literal_priority"]


@dataclass(frozen=True)
class CanonicalSlotConstraint:
    pos: int
    kind: str
    value: Optional[CanonicalSlotValue]


@dataclass(frozen=True)
class CanonicalCompoundPolicy:
    kind: str
    connective: Optional[str]


@dataclass(frozen=True)
class CanonicalMatchSpec:
    width: int
    slots: tuple[CanonicalSlotConstraint, ...]
    mask: str
    equals_span: Optional[EqualsSpan]
    compound: Optional[CanonicalCompoundPolicy]
    ranking: RankingPolicy
    candidate_scope: CandidateScope
    code_mode: Optional[str]
    phoneme_alternatives: Optional["CanonicalPhonemeAlternatives"]


@dataclass(frozen=True)
class CanonicalPhonemeAlternatives:
    initial: CanonicalMatchSpec
    final: CanonicalMatchSpec


def _value(value: Any) -> Optional[CanonicalSlotValue]:
    if value is None:
        return None
    if isinstance(value, (set, frozenset, tuple, list)):
        return tuple(sorted(str(item) for item in value))
    return str(value)


def _slot_key(slot: CanonicalSlotConstraint) -> tuple[int, str, str]:
    return slot.pos, slot.kind, repr(slot.value)


def _freeze_span(span: Optional[EqualsSpan]) -> Optional[EqualsSpan]:
    if span is None:
        return None
    return EqualsSpan(
        ref_literal=str(span.ref_literal),
        ref_jyutping=None if span.ref_jyutping is None else str(span.ref_jyutping),
        start_pos=span.start_pos,
        dimension=span.dimension,
        phoneme_anchor_only=bool(span.phoneme_anchor_only),
        whole_word=bool(span.whole_word),
    )


def finalize_canonical_match_spec(
    *,
    width: int,
    slots: list[SlotConstraint] | tuple[SlotConstraint, ...] = (),
    mask: Optional[str] = None,
    equals_span: Optional[EqualsSpan] = None,
    compound_kind: Optional[str] = None,
    connective: Optional[str] = None,
    ranking: RankingPolicy = "default",
    candidate_scope: CandidateScope = "bounded",
    code_mode: Optional[str] = None,
    phoneme_alternatives: Optional[CanonicalPhonemeAlternatives] = None,
) -> CanonicalMatchSpec:
    if not isinstance(width, int) or width <= 0:
        raise ValueError(f"MatchSpec width must be a positive integer: {width}")

    canonical_slots = tuple(
        sorted(
            (
                CanonicalSlotConstraint(slot.pos, slot.kind, _value(slot.value))
                for slot in slots
            ),
            key=_slot_key,
        )
    )
    for slot in canonical_slots:
        if not isinstance(slot.pos, int) or slot.pos < 0 or slot.pos >= width:
            raise ValueError(f"MatchSpec slot position out of range: {slot.pos}")
    if len(set(_slot_key(slot) for slot in canonical_slots)) != len(canonical_slots):
        raise ValueError("MatchSpec duplicate slot")

    canonical_mask = "?" * width if not mask else str(mask)
    if len(canonical_mask) != width:
        raise ValueError(f"MatchSpec mask width mismatch: {len(canonical_mask)} != {width}")

    span = _freeze_span(equals_span)
    if span is not None and not 0 <= span.start_pos < width:
        raise ValueError(f"MatchSpec equals span position out of range: {span.start_pos}")

    compound = (
        CanonicalCompoundPolicy(str(compound_kind), connective)
        if compound_kind is not None
        else None
    )
    return CanonicalMatchSpec(
        width=width,
        slots=canonical_slots,
        mask=canonical_mask,
        equals_span=span,
        compound=compound,
        ranking=ranking,
        candidate_scope=candidate_scope,
        code_mode=code_mode,
        phoneme_alternatives=phoneme_alternatives,
    )


def canonicalize_legacy_match_spec(spec: MatchSpec) -> CanonicalMatchSpec:
    """Short-lived adapter for callers not yet moved to the compiler seam."""
    raw = spec.extra
    initial = raw.get("dual_initial_spec")
    final = raw.get("dual_final_spec")
    alternatives = (
        CanonicalPhonemeAlternatives(
            canonicalize_legacy_match_spec(initial),
            canonicalize_legacy_match_spec(final),
        )
        if isinstance(initial, MatchSpec) and isinstance(final, MatchSpec)
        else None
    )
    return finalize_canonical_match_spec(
        width=spec.width,
        slots=spec.slots,
        mask=spec.mask,
        equals_span=get_equals_span(spec),
        compound_kind=spec.compound_kind,
        connective=raw.get("connective") if isinstance(raw.get("connective"), str) else None,
        ranking="literal_priority" if spec.literal_priority else "default",
        candidate_scope="complete" if raw.get("workbench_full_bucket_scan") else "bounded",
        code_mode=raw.get("code_mode") if isinstance(raw.get("code_mode"), str) else None,
        phoneme_alternatives=alternatives,
    )


def _json_value(value: Optional[CanonicalSlotValue]) -> object:
    if value is None:
        return None
    return list(value) if isinstance(value, tuple) else value


def canonical_match_spec_to_json(spec: CanonicalMatchSpec) -> dict[str, object]:
    """Stable projection consumed by the shared Python／TypeScript corpus."""
    return {
        "width": spec.width,
        "mask": spec.mask,
        "slots": [
            {"pos": slot.pos, "kind": slot.kind, "value": _json_value(slot.value)}
            for slot in spec.slots
        ],
        "equals_span": (
            {
                "ref_literal": spec.equals_span.ref_literal,
                "ref_jyutping": spec.equals_span.ref_jyutping,
                "start_pos": spec.equals_span.start_pos,
                "dimension": spec.equals_span.dimension,
                "phoneme_anchor_only": spec.equals_span.phoneme_anchor_only,
                "whole_word": spec.equals_span.whole_word,
            }
            if spec.equals_span is not None
            else None
        ),
        "compound": (
            {"kind": spec.compound.kind, "connective": spec.compound.connective}
            if spec.compound is not None
            else None
        ),
        "ranking": spec.ranking,
        "candidate_scope": spec.candidate_scope,
        "code_mode": spec.code_mode,
        "phoneme_alternatives": (
            {
                "initial": canonical_match_spec_to_json(spec.phoneme_alternatives.initial),
                "final": canonical_match_spec_to_json(spec.phoneme_alternatives.final),
            }
            if spec.phoneme_alternatives is not None
            else None
        ),
    }


__all__ = [
    "CanonicalCompoundPolicy",
    "CanonicalMatchSpec",
    "CanonicalPhonemeAlternatives",
    "CanonicalSlotConstraint",
    "canonical_match_spec_to_json",
    "canonicalize_legacy_match_spec",
    "finalize_canonical_match_spec",
]
