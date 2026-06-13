"""Central MatchSpec factory (candidate 1): ParsedQuery → MatchSpec. No DB access."""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.position_match import MatchSpec
    from app.services.query_parse import ParsedQuery

HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")


def build_match_spec(parsed: "ParsedQuery") -> Optional["MatchSpec"]:
    """Single interface: normalize any position-type ParsedQuery to MatchSpec."""
    from app.services.query_parse import (
        CodeTailQuery,
        CompoundAntQuery,
        EqualsQuery,
        HybridCodeQuery,
        LiteralRefQuery,
        MaskQuery,
        RhymeAnchorQuery,
    )
    from app.services.position_match import MatchSpec, SlotConstraint, build_equals_match_spec
    from app.services.word_query_parser import build_mask_from_slots, parse_mask_query

    if isinstance(parsed, EqualsQuery):
        return build_equals_match_spec(parsed.raw_q)

    if isinstance(parsed, CompoundAntQuery):
        spec = MatchSpec(width=2, code_prefix=parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(
                    pos=1,
                    kind="final_anchor",
                    value=parsed.rhyme_char,
                )
            )
        return spec

    if isinstance(parsed, CodeTailQuery):
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_digits)
        if parsed.constraint == "literal":
            m = build_mask_from_slots("", parsed.width, parsed.anchor_pos)
            m = m[: parsed.anchor_pos] + parsed.anchor
            spec.mask = m
            spec.slots.append(
                SlotConstraint(pos=parsed.anchor_pos, kind="literal_char", value=parsed.anchor)
            )
        else:
            kind = "final_anchor" if parsed.constraint == "final" else "initial_anchor"
            spec.slots.append(
                SlotConstraint(pos=parsed.anchor_pos, kind=kind, value=parsed.anchor)
            )
            spec.mask = build_mask_from_slots("", parsed.width, parsed.anchor_pos)
        return spec

    if isinstance(parsed, LiteralRefQuery):
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_digits)
        spec.slots.append(
            SlotConstraint(pos=parsed.width - 1, kind="literal_char", value=parsed.literal_char)
        )
        spec.mask = "?" * (parsed.width - 1) + parsed.literal_char
        return spec

    if isinstance(parsed, RhymeAnchorQuery):
        spec = MatchSpec(width=parsed.width)
        kind = "final_anchor" if parsed.constraint == "final" else "initial_anchor"
        spec.slots.append(
            SlotConstraint(pos=parsed.anchor_pos, kind=kind, value=parsed.anchor)
        )
        spec.mask = build_mask_from_slots(parsed.slots, parsed.width, parsed.anchor_pos)
        return spec

    if isinstance(parsed, HybridCodeQuery):
        hybrid_match = HYBRID_CODE_RE.match(parsed.raw_q)
        if not hybrid_match:
            return MatchSpec(width=0)
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)
        full_code = num_prefix + num_suffix
        return MatchSpec(
            width=len(full_code),
            code_prefix=full_code,
            hybrid_ref_chars=ref_chars,
            hybrid_ref_pos=max(0, len(num_prefix) - 1),
        )

    if isinstance(parsed, MaskQuery):
        expected_len, _, literal_positions = parse_mask_query(parsed.raw_q)
        spec = MatchSpec(
            width=expected_len,
            literal_priority=True,
            mask=parsed.raw_q,
        )
        for i, ch in enumerate(parsed.raw_q):
            if ch.isdigit():
                spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=ch))
        spec.extra["literal_positions"] = literal_positions
        return spec

    return None


__all__ = ["HYBRID_CODE_RE", "build_match_spec"]
