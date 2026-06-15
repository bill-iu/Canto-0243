"""缺字型家族 ParsedQuery → MatchSpec 正規化（CONTEXT § 查詢分派）。"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.services.query_parse import (
    HYBRID_CODE_RE,
    CodeTailQuery,
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    LiteralRefQuery,
    MaskQuery,
    ParsedQuery,
    RhymeAnchorQuery,
)
from app.services.word_query_parser import build_mask_from_slots, parse_mask_query


def is_mask_family_query(parsed: Any) -> bool:
    """是否為缺字型查詢家族（不含 ~~ / !! 複合詞）。"""
    return isinstance(
        parsed,
        (
            HybridTailEqualsAliasQuery,
            EqualsQuery,
            MaskQuery,
            HybridCodeQuery,
            RhymeAnchorQuery,
            CodeTailQuery,
            LiteralRefQuery,
        ),
    )


def normalize_mask_family_parsed(parsed: ParsedQuery) -> ParsedQuery:
    """別名改寫（如 HybridTailEqualsAlias → HybridCode），在查詢分派層完成。"""
    if isinstance(parsed, HybridTailEqualsAliasQuery):
        return HybridCodeQuery(raw_q=parsed.hybrid_q)
    return parsed


def build_equals_match_spec(q: str) -> Optional["MatchSpec"]:
    """查詢字串 → 等號 MatchSpec（純函式，無 DB）。語意見 CONTEXT § 碼夾等號查詢。"""
    from app.services.position_match import MatchSpec

    match = re.match(r"^(\d*)(=)?([一-龥]+)?(=)?(\d*)$", q)
    if not match:
        return None
    target_str = match.group(3) or ""
    if not target_str:
        return None

    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    target_length = len(target_str)
    expected_length = len(left_code) + len(right_code) or target_length
    start_pos = max(0, len(left_code) - target_length)
    full_code = left_code + right_code

    return MatchSpec(
        width=expected_length,
        code_prefix=full_code if full_code else None,
        ref_literal=target_str,
        ref_start_pos=start_pos,
        ref_dimension="final" if right_equal else "initial",
        phoneme_anchor_only=bool(left_code and (right_code or inner_equal)),
        whole_word_phoneme_match=(start_pos == 0 and target_length == expected_length),
    )


def build_mask_family_match_spec(parsed: Any) -> Optional["MatchSpec"]:
    """缺字家族 ParsedQuery → MatchSpec。無 DB。"""
    from app.services.position_match import MatchSpec, SlotConstraint

    if isinstance(parsed, EqualsQuery):
        return build_equals_match_spec(parsed.raw_q)

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
