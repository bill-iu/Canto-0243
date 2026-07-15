"""查詢種類 → MatchSpec builders（CONTEXT § 查詢種類；ADR-0002 Phase 1）。"""
from __future__ import annotations

from typing import Callable, Optional

from app.services.position_match import MatchSpec, SlotConstraint
from app.services.query_types import (
    CodeRefMiddleRhymeQuery,
    JyutpingAnchorQuery,
    LiteralRefQuery,
    MaskQuery,
    ParsedQuery,
    PartialRhymeMaskQuery,
    QueryKind,
    RhymeAnchorQuery,
    PlusAnchorQuery,
    TripleRhymeAnchorQuery,
    WildcardCodeAnchorQuery,
)
from app.services.query_grammar.mask import build_mask_from_slots, parse_mask_query
from app.services.position_match.mask_adapter import append_code_digit_slots


def _apply_jyutping_anchor_code_slots(spec: MatchSpec, parsed: JyutpingAnchorQuery) -> None:
    if parsed.code_slots:
        for pos, digit in parsed.code_slots:
            spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=digit))
    elif parsed.code_prefix and parsed.width == len(parsed.code_prefix):
        append_code_digit_slots(spec, parsed.code_prefix)


def _build_jyutping_anchor_match_spec(parsed: JyutpingAnchorQuery) -> MatchSpec:
    spec = MatchSpec(width=parsed.width)
    spec.mask = "?" * parsed.width
    spec.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind=parsed.anchor_kind,
            value=parsed.anchor_value,
        )
    )
    _apply_jyutping_anchor_code_slots(spec, parsed)
    return spec


def build_jyutping_dual_match_specs(parsed: JyutpingAnchorQuery) -> tuple[MatchSpec, MatchSpec]:
    """歧義粵拼錨 → 聲母維與韻母維 MatchSpec（ADR-0009）。"""

    def _base() -> MatchSpec:
        spec = MatchSpec(width=parsed.width)
        spec.mask = "?" * parsed.width
        _apply_jyutping_anchor_code_slots(spec, parsed)
        return spec

    initial = _base()
    initial.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="initial_letters",
            value=(parsed.dual_initial_value or parsed.anchor_value),
        )
    )
    final = _base()
    final.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="rhyme_letters",
            value=parsed.anchor_value,
        )
    )
    return initial, final


MatchSpecBuilder = Callable[[ParsedQuery], Optional[MatchSpec]]


def _spec_equals(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.equals import to_match_spec as equals_to_match_spec

    return equals_to_match_spec(parsed)


def _spec_serial(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.serial import to_match_spec as serial_to_match_spec

    return serial_to_match_spec(parsed)


def _spec_partial_rhyme_mask(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.PARTIAL_RHYME_MASK
    q = parsed  # type: PartialRhymeMaskQuery
    spec = MatchSpec(width=q.width, mask=q.pattern)
    spec.extra["partial_rhyme_mask"] = True
    for pos, ch in q.anchors:
        spec.slots.append(SlotConstraint(pos=pos, kind="final_anchor", value=ch))
    return spec


def _spec_partial_initial_mask(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.PARTIAL_INITIAL_MASK
    q = parsed  # type: PartialInitialMaskQuery
    spec = MatchSpec(width=q.width, mask=q.pattern)
    spec.extra["partial_initial_mask"] = True
    for pos, ch in q.anchors:
        spec.slots.append(SlotConstraint(pos=pos, kind="initial_anchor", value=ch))
    return spec


def _spec_plus_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.PLUS_ANCHOR
    q = parsed  # type: PlusAnchorQuery
    spec = MatchSpec(width=q.width)
    spec.mask = "?" * q.width
    for pos, d in q.code_slots:
        spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=d))
    if not q.code_slots:
        append_code_digit_slots(spec, q.code_prefix)
    if q.constraint == "literal":
        spec.slots.append(
            SlotConstraint(pos=q.anchor_pos, kind="literal_char", value=q.anchor)
        )
        spec.mask = spec.mask[: q.anchor_pos] + q.anchor + spec.mask[q.anchor_pos + 1 :]
        return spec
    if q.constraint == "final":
        spec.slots.append(
            SlotConstraint(pos=q.anchor_pos, kind="final_anchor", value=q.anchor)
        )
        return spec
    if q.constraint == "initial":
        spec.slots.append(
            SlotConstraint(pos=q.anchor_pos, kind="initial_anchor", value=q.anchor)
        )
    return spec


def _spec_literal_ref(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.LITERAL_REF
    q = parsed  # type: LiteralRefQuery
    spec = MatchSpec(width=q.width)
    append_code_digit_slots(spec, q.code_digits)
    spec.slots.append(
        SlotConstraint(pos=q.width - 1, kind="literal_char", value=q.literal_char)
    )
    spec.mask = "?" * (q.width - 1) + q.literal_char
    return spec


def _spec_wildcard_code_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.WILDCARD_CODE_ANCHOR
    q = parsed  # type: WildcardCodeAnchorQuery
    spec = MatchSpec(width=q.width)
    spec.mask = "?" * q.width
    for slot in q.slots:
        spec.slots.append(
            SlotConstraint(pos=slot["pos"], kind=slot["kind"], value=slot["value"])
        )
        if slot["kind"] == "literal_char":
            spec.mask = (
                spec.mask[: slot["pos"]] + slot["value"] + spec.mask[slot["pos"] + 1 :]
            )
    return spec


def _spec_code_ref_middle_rhyme(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.CODE_REF_MIDDLE_RHYME
    q = parsed  # type: CodeRefMiddleRhymeQuery
    spec = MatchSpec(width=q.width)
    spec.mask = "?" * q.width
    for slot in q.slots:
        spec.slots.append(
            SlotConstraint(pos=slot["pos"], kind=slot["kind"], value=slot["value"])
        )
    return spec


def _spec_rhyme_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.RHYME_ANCHOR
    q = parsed  # type: RhymeAnchorQuery
    spec = MatchSpec(width=q.width)
    kind = "final_anchor" if q.constraint == "final" else "initial_anchor"
    spec.slots.append(SlotConstraint(pos=q.anchor_pos, kind=kind, value=q.anchor))
    spec.mask = build_mask_from_slots(q.slots, q.width, q.anchor_pos)
    return spec


def _spec_triple_rhyme_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.TRIPLE_RHYME_ANCHOR
    q = parsed  # type: TripleRhymeAnchorQuery
    spec = MatchSpec(width=q.width)
    spec.slots.append(
        SlotConstraint(pos=q.anchor_pos, kind="final_anchor", value=q.anchor)
    )
    spec.mask = "?" * q.width
    return spec


def _spec_jyutping_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.JYUTPING_ANCHOR
    q = parsed  # type: JyutpingAnchorQuery
    if q.dual_phoneme:
        initial, final = build_jyutping_dual_match_specs(q)
        carrier = MatchSpec(width=q.width)
        _apply_jyutping_anchor_code_slots(carrier, q)
        carrier.extra["dual_phoneme"] = True
        carrier.extra["dual_initial_spec"] = initial
        carrier.extra["dual_final_spec"] = final
        return carrier
    return _build_jyutping_anchor_match_spec(q)


def _spec_mask(parsed: ParsedQuery) -> Optional[MatchSpec]:
    assert parsed.kind == QueryKind.MASK
    q = parsed  # type: MaskQuery
    expected_len, _, literal_positions = parse_mask_query(q.raw_q)
    spec = MatchSpec(
        width=expected_len,
        literal_priority=True,
        mask=q.raw_q,
    )
    for i, ch in enumerate(q.raw_q):
        if ch.isdigit():
            spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=ch))
    spec.extra["literal_positions"] = literal_positions
    return spec


def _spec_ping_ze_serial(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.ping_zak import to_match_spec as pingze_to_match_spec

    return pingze_to_match_spec(parsed)


def _spec_relation(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.relation import to_match_spec as relation_to_match_spec

    return relation_to_match_spec(parsed)


MATCH_SPEC_BUILDERS: dict[QueryKind, MatchSpecBuilder] = {
    QueryKind.EQUALS: _spec_equals,
    QueryKind.PREFIX_WILDCARD_EQUALS: _spec_serial,
    QueryKind.PARTIAL_RHYME_MASK: _spec_partial_rhyme_mask,
    QueryKind.PARTIAL_INITIAL_MASK: _spec_partial_initial_mask,
    QueryKind.SERIAL_PHONEME: _spec_serial,
    QueryKind.PLUS_ANCHOR: _spec_plus_anchor,
    QueryKind.LITERAL_REF: _spec_literal_ref,
    QueryKind.WILDCARD_CODE_ANCHOR: _spec_wildcard_code_anchor,
    QueryKind.CODE_REF_MIDDLE_RHYME: _spec_code_ref_middle_rhyme,
    QueryKind.RHYME_ANCHOR: _spec_rhyme_anchor,
    QueryKind.TRIPLE_RHYME_ANCHOR: _spec_triple_rhyme_anchor,
    QueryKind.JYUTPING_ANCHOR: _spec_jyutping_anchor,
    QueryKind.MASK: _spec_mask,
    QueryKind.PING_ZE_SERIAL: _spec_ping_ze_serial,
    QueryKind.COMPOUND_SYN: _spec_relation,
    QueryKind.COMPOUND_CONNECT_SYN: _spec_relation,
    QueryKind.COMPOUND_DOUBLED_SYLLABLE: _spec_relation,
    QueryKind.COMPOUND_ANT: _spec_relation,
    QueryKind.COMPOUND_CONNECT_ANT: _spec_relation,
}


def build_match_spec_for_parsed(parsed: ParsedQuery) -> Optional[MatchSpec]:
    """ParsedQuery.kind → MatchSpec（查詢種類註冊表入口）。"""
    builder = MATCH_SPEC_BUILDERS.get(parsed.kind)
    if builder is None:
        return None
    return builder(parsed)


__all__ = ["MATCH_SPEC_BUILDERS", "MatchSpecBuilder", "build_jyutping_dual_match_specs", "build_match_spec_for_parsed"]
