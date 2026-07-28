"""Canonical immutable MatchSpec value seam.

The migration adapter in this module lets existing callers move one seam at a
time. It has no database knowledge; execution adapters choose their physical
candidate plan after receiving the semantic value.
"""

from __future__ import annotations

import re
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
    mask_token: Optional[str] = None


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


def _slot_class_key(slot: CanonicalSlotConstraint) -> tuple[int, str]:
    return slot.pos, slot.kind


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

    raw_mask = "?" * width if not mask else str(mask)
    if len(raw_mask) != width:
        raise ValueError(f"MatchSpec mask width mismatch: {len(raw_mask)} != {width}")

    mutable_slots = [
        CanonicalSlotConstraint(slot.pos, slot.kind, _value(slot.value))
        for slot in slots
    ]
    for slot in mutable_slots:
        if not isinstance(slot.pos, int) or slot.pos < 0 or slot.pos >= width:
            raise ValueError(f"MatchSpec slot position out of range: {slot.pos}")
    for pos, token in enumerate(raw_mask):
        if token in {"?", "_", "%"}:
            continue
        owner_index = next(
            (
                index
                for index, slot in enumerate(mutable_slots)
                if slot.pos == pos and isinstance(slot.value, str) and slot.value == token
            ),
            None,
        )
        if owner_index is None and not token.isdigit():
            mutable_slots.append(
                CanonicalSlotConstraint(pos, "literal_char", token, token)
            )
            continue
        if owner_index is None:
            raise ValueError(f"MatchSpec mask token has no owning slot: {pos}:{token}")
        owner = mutable_slots[owner_index]
        mutable_slots[owner_index] = CanonicalSlotConstraint(
            owner.pos, owner.kind, owner.value, token
        )
    canonical_slots = tuple(sorted(mutable_slots, key=_slot_key))
    seen_slots: dict[tuple[int, str], CanonicalSlotValue | None] = {}
    for slot in canonical_slots:
        key = _slot_class_key(slot)
        if key in seen_slots:
            label = "duplicate" if seen_slots[key] == slot.value else "conflicting"
            raise ValueError(f"MatchSpec {label} slot: {key}")
        seen_slots[key] = slot.value

    mask_tokens = ["?"] * width
    for slot in canonical_slots:
        if slot.mask_token:
            mask_tokens[slot.pos] = slot.mask_token
    canonical_mask = "".join(mask_tokens)

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


def canonical_match_spec_to_legacy(spec: CanonicalMatchSpec) -> MatchSpec:
    """Transitional execution adapter; keep mutable shape knowledge here."""
    extra: dict[str, Any] = {}
    if spec.equals_span is not None:
        extra["equals_span"] = spec.equals_span
    if spec.compound and spec.compound.connective:
        extra["connective"] = spec.compound.connective
    if spec.code_mode:
        extra["code_mode"] = spec.code_mode
    if spec.candidate_scope == "complete":
        extra["workbench_full_bucket_scan"] = True
    literal_positions = [
        (pos, char)
        for pos, char in enumerate(spec.mask)
        if re.fullmatch(r"[\u4e00-\u9fff]", char)
    ]
    if literal_positions:
        extra["literal_positions"] = literal_positions
    if (
        spec.equals_span is not None
        and spec.equals_span.start_pos == 1
        and spec.equals_span.phoneme_anchor_only
    ):
        extra["prefix_wildcard_equals"] = True
    has_final = any(slot.kind == "final_anchor" for slot in spec.slots)
    has_initial = any(slot.kind == "initial_anchor" for slot in spec.slots)
    anchor_count = sum(
        slot.kind in {"final_anchor", "initial_anchor"} for slot in spec.slots
    )
    if spec.width == 4 and anchor_count >= 2 and has_final and "?" in spec.mask:
        extra["partial_rhyme_mask"] = True
    if spec.width == 4 and anchor_count >= 2 and has_initial and "?" in spec.mask:
        extra["partial_initial_mask"] = True
    if spec.phoneme_alternatives:
        extra["dual_phoneme"] = True
        extra["dual_initial_spec"] = canonical_match_spec_to_legacy(spec.phoneme_alternatives.initial)
        extra["dual_final_spec"] = canonical_match_spec_to_legacy(spec.phoneme_alternatives.final)
    return MatchSpec(
        width=spec.width,
        slots=[
            SlotConstraint(pos=slot.pos, kind=slot.kind, value=slot.value)
            for slot in spec.slots
        ],
        literal_priority=spec.ranking == "literal_priority",
        mask=spec.mask,
        compound_kind=spec.compound.kind if spec.compound else None,
        extra=extra,
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
    "canonical_match_spec_to_legacy",
    "canonicalize_legacy_match_spec",
    "finalize_canonical_match_spec",
]
