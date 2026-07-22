"""plan → MatchSpec (L1) — mirror of client/src/workbench/build-match-spec.ts."""

from __future__ import annotations

from typing import Any

from app.schemas.workbench_schema import ReplacementPlanV1
from app.services.position_match.spec import EqualsSpan, MatchSpec, SlotConstraint, attach_equals_span


def build_match_spec(plan: ReplacementPlanV1) -> MatchSpec:
    mask = ["?"] * plan.width
    slots: list[SlotConstraint] = []
    for item in plan.slots:
        value = {
            "code_digit": item.digit,
            "literal_char": item.literal,
            "final_anchor": item.ref,
            "initial_anchor": item.ref,
            "tone_class": item.tone_class,
        }[item.kind]
        slots.append(SlotConstraint(pos=item.pos, kind=item.kind, value=value))
        if item.kind == "literal_char" and item.literal:
            mask[item.pos] = item.literal
    spec = MatchSpec(width=plan.width, slots=slots, mask="".join(mask))
    for kind, dimension in (("final_anchor", "final"), ("initial_anchor", "initial")):
        anchor_items = sorted(
            (item for item in plan.slots if item.kind == kind),
            key=lambda item: item.pos,
        )
        anchors = sorted((slot for slot in slots if slot.kind == kind), key=lambda slot: slot.pos)
        positions = [slot.pos for slot in anchors]
        if (
            len(anchors) < 2
            or not all(item.ref_jyutping for item in anchor_items)
            or positions != list(range(positions[0], positions[-1] + 1))
        ):
            continue
        spec.slots = [slot for slot in slots if slot.kind != kind]
        attach_equals_span(spec, EqualsSpan(
            ref_literal="".join(str(slot.value or "") for slot in anchors),
            ref_jyutping=" ".join(item.ref_jyutping or "" for item in anchor_items),
            start_pos=positions[0],
            dimension=dimension,
            phoneme_anchor_only=True,
            whole_word=positions[0] == 0 and len(positions) == plan.width,
        ))
        if positions[0] > 0 and positions[-1] == plan.width - 1:
            spec.extra["prefix_wildcard_equals"] = True
        break
    return spec


def match_spec_to_canonical(spec: MatchSpec) -> dict[str, Any]:
    """Stable JSON shape for L1 parity with TS matchSpecToCanonical."""
    slots: list[dict[str, Any]] = []
    for slot in spec.slots:
        value = slot.value
        if isinstance(value, set):
            value = sorted(value)
        slots.append({"pos": slot.pos, "kind": slot.kind, "value": value})
    extra: dict[str, Any] = {}
    raw_span = spec.extra.get("equals_span")
    if raw_span is not None:
        if isinstance(raw_span, EqualsSpan):
            extra["equals_span"] = {
                "ref_literal": raw_span.ref_literal,
                "ref_jyutping": raw_span.ref_jyutping,
                "start_pos": raw_span.start_pos,
                "dimension": raw_span.dimension,
                "phoneme_anchor_only": raw_span.phoneme_anchor_only,
                "whole_word": raw_span.whole_word,
            }
        elif isinstance(raw_span, dict):
            extra["equals_span"] = {
                "ref_literal": raw_span.get("ref_literal") or "",
                "ref_jyutping": raw_span.get("ref_jyutping"),
                "start_pos": raw_span.get("start_pos") or 0,
                "dimension": raw_span.get("dimension") or "final",
                "phoneme_anchor_only": bool(raw_span.get("phoneme_anchor_only")),
                "whole_word": bool(raw_span.get("whole_word")),
            }
    if spec.extra.get("prefix_wildcard_equals"):
        extra["prefix_wildcard_equals"] = True
    return {
        "width": spec.width,
        "mask": spec.mask or "",
        "slots": slots,
        "extra": extra,
    }


__all__ = ["build_match_spec", "match_spec_to_canonical"]
