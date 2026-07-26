"""Strict ParsedQuery → canonical MatchSpec compiler seam (migration shell)."""

from __future__ import annotations

import re
from typing import TypeAlias

from app.services._generated.query_kind_registry import MATCH_SPEC_KINDS, QueryKind, uses_match_spec_kind
from app.services.position_match.canonical import (
    CanonicalPhonemeAlternatives,
    CanonicalMatchSpec,
    canonicalize_legacy_match_spec,
    finalize_canonical_match_spec,
)
from app.services.position_match.spec import EqualsSpan, SlotConstraint
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_types import (
    CodeRefMiddleRhymeQuery,
    CompoundAntQuery,
    CompoundConnectAntQuery,
    CompoundConnectSynQuery,
    CompoundDoubledSyllableQuery,
    CompoundSynQuery,
    EqualsQuery,
    JyutpingAnchorQuery,
    LiteralRefQuery,
    MaskQuery,
    PartialInitialMaskQuery,
    PartialRhymeMaskQuery,
    ParsedQuery,
    PingZeSerialQuery,
    PlusAnchorQuery,
    PrefixWildcardEqualsQuery,
    RhymeAnchorQuery,
    SerialPhonemeAnchorQuery,
    TripleRhymeAnchorQuery,
    WildcardCodeAnchorQuery,
)
from app.utils.han import HAN_CLASS

MatchSpecQuery: TypeAlias = (
    EqualsQuery
    | PrefixWildcardEqualsQuery
    | PartialRhymeMaskQuery
    | PartialInitialMaskQuery
    | SerialPhonemeAnchorQuery
    | PlusAnchorQuery
    | LiteralRefQuery
    | WildcardCodeAnchorQuery
    | CodeRefMiddleRhymeQuery
    | RhymeAnchorQuery
    | TripleRhymeAnchorQuery
    | JyutpingAnchorQuery
    | MaskQuery
    | PingZeSerialQuery
    | CompoundSynQuery
    | CompoundConnectSynQuery
    | CompoundDoubledSyllableQuery
    | CompoundAntQuery
    | CompoundConnectAntQuery
)


def require_match_spec_query(parsed: ParsedQuery) -> MatchSpecQuery:
    """Narrow general parser output at the query dispatch seam."""
    if not uses_match_spec_kind(parsed.kind):
        raise ValueError(f"query kind does not use MatchSpec: {parsed.kind}")
    return parsed  # type: ignore[return-value]


def compile_query(query: MatchSpecQuery) -> CanonicalMatchSpec:
    """Compile one eligible query to a complete semantic value."""
    if query.kind not in MATCH_SPEC_KINDS:
        raise ValueError(f"query kind does not use MatchSpec: {query.kind}")
    if query.kind == QueryKind.EQUALS:
        return _compile_equals(query)
    if query.kind == QueryKind.PREFIX_WILDCARD_EQUALS:
        return _compile_prefix_wildcard_equals(query)
    if query.kind == QueryKind.SERIAL_PHONEME:
        return _compile_serial_phoneme(query)
    if query.kind == QueryKind.PLUS_ANCHOR:
        return _compile_plus_anchor(query)
    if query.kind == QueryKind.LITERAL_REF:
        return _compile_literal_ref(query)
    if query.kind == QueryKind.PARTIAL_RHYME_MASK:
        return _compile_partial_mask(query, "final_anchor")
    if query.kind == QueryKind.PARTIAL_INITIAL_MASK:
        return _compile_partial_mask(query, "initial_anchor")
    if query.kind == QueryKind.CODE_REF_MIDDLE_RHYME:
        return _compile_code_ref_middle_rhyme(query)
    if query.kind == QueryKind.RHYME_ANCHOR:
        return _compile_rhyme_anchor(query)
    if query.kind == QueryKind.TRIPLE_RHYME_ANCHOR:
        return _compile_triple_rhyme_anchor(query)
    if query.kind == QueryKind.MASK:
        return _compile_mask(query)
    if query.kind == QueryKind.WILDCARD_CODE_ANCHOR:
        return _compile_wildcard_code_anchor(query)
    if query.kind == QueryKind.COMPOUND_SYN:
        return _compile_compound(query, "syn")
    if query.kind == QueryKind.COMPOUND_ANT:
        return _compile_compound(query, "ant")
    if query.kind == QueryKind.COMPOUND_CONNECT_SYN:
        return _compile_compound(query, "syn")
    if query.kind == QueryKind.COMPOUND_CONNECT_ANT:
        return _compile_compound(query, "ant")
    if query.kind == QueryKind.COMPOUND_DOUBLED_SYLLABLE:
        return _compile_doubled_syllable(query)
    if query.kind == QueryKind.JYUTPING_ANCHOR:
        return _compile_jyutping_anchor(query)
    legacy = build_match_spec_for_parsed(query)
    if legacy is None:
        raise ValueError(f"MatchSpec compiler has no implementation for {query.kind}")
    return canonicalize_legacy_match_spec(legacy)


_FRAMED_EQUALS_RE = re.compile(rf"^(\d*)(\^|=)?([{HAN_CLASS}]+)(=)?(\d*)$")


def _equals_draft(raw: str) -> dict:
    match = _FRAMED_EQUALS_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"invalid equals MatchSpec query: {raw}")
    target = match.group(3) or ""
    left = match.group(1) or ""
    right = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_mark = bool(match.group(2))
    target_length = len(target)
    width = len(left) + len(right) or target_length
    start_pos = max(0, len(left) - target_length)
    return {
        "width": width,
        "slots": [SlotConstraint(pos=pos, kind="code_digit", value=digit) for pos, digit in enumerate(left + right)],
        "equals_span": EqualsSpan(
            ref_literal=target,
            start_pos=start_pos,
            dimension="final" if right_equal else "initial",
            phoneme_anchor_only=bool(left and (right or inner_mark)),
            whole_word=start_pos == 0 and target_length == width,
        ),
    }


def _compile_equals(query: EqualsQuery) -> CanonicalMatchSpec:
    return finalize_canonical_match_spec(**_equals_draft(query.raw_q))


def _compile_prefix_wildcard_equals(query: PrefixWildcardEqualsQuery) -> CanonicalMatchSpec:
    draft = _equals_draft(query.inner_q)
    span = draft["equals_span"]
    draft["width"] = query.width
    draft["mask"] = "?" * query.width
    draft["equals_span"] = EqualsSpan(
        ref_literal=span.ref_literal,
        ref_jyutping=span.ref_jyutping,
        start_pos=1,
        dimension=span.dimension,
        phoneme_anchor_only=True,
        whole_word=False,
    )
    return finalize_canonical_match_spec(**draft)


def _compile_serial_phoneme(query: SerialPhonemeAnchorQuery) -> CanonicalMatchSpec:
    anchor_kind = "final_anchor" if query.constraint == "final" else "initial_anchor"
    slots = [
        *(
            SlotConstraint(pos=pos, kind="code_digit", value=value)
            for pos, value in query.code_slots
        ),
        *(
            SlotConstraint(pos=pos, kind=anchor_kind, value=value)
            for pos, value in query.anchors
        ),
    ]
    return finalize_canonical_match_spec(
        width=query.width,
        mask=query.mask if len(query.mask) == query.width else "?" * query.width,
        slots=slots,
    )


def _compile_plus_anchor(query: PlusAnchorQuery) -> CanonicalMatchSpec:
    slots = [
        SlotConstraint(pos=pos, kind="code_digit", value=value)
        for pos, value in query.code_slots
    ]
    if not slots and query.code_prefix:
        slots.extend(
            SlotConstraint(pos=pos, kind="code_digit", value=value)
            for pos, value in enumerate(query.code_prefix)
        )
    mask = ["?"] * query.width
    if query.constraint == "literal":
        slots.append(SlotConstraint(pos=query.anchor_pos, kind="literal_char", value=query.anchor))
        mask[query.anchor_pos] = query.anchor
    else:
        kind = "final_anchor" if query.constraint == "final" else "initial_anchor"
        slots.append(SlotConstraint(pos=query.anchor_pos, kind=kind, value=query.anchor))
    return finalize_canonical_match_spec(width=query.width, slots=slots, mask="".join(mask))


def _compile_literal_ref(query: LiteralRefQuery) -> CanonicalMatchSpec:
    slots = [
        SlotConstraint(pos=pos, kind="code_digit", value=value)
        for pos, value in enumerate(query.code_digits)
    ]
    slots.append(
        SlotConstraint(pos=query.literal_pos, kind="literal_char", value=query.literal_char)
    )
    mask = "?" * query.literal_pos + query.literal_char + "?" * (query.width - query.literal_pos - 1)
    return finalize_canonical_match_spec(width=query.width, slots=slots, mask=mask)


def _compile_partial_mask(
    query: PartialRhymeMaskQuery | PartialInitialMaskQuery,
    kind: str,
) -> CanonicalMatchSpec:
    return finalize_canonical_match_spec(
        width=query.width,
        mask=query.pattern,
        slots=[SlotConstraint(pos=pos, kind=kind, value=value) for pos, value in query.anchors],
    )


def _compile_code_ref_middle_rhyme(query: CodeRefMiddleRhymeQuery) -> CanonicalMatchSpec:
    return finalize_canonical_match_spec(
        width=query.width,
        mask="?" * query.width,
        slots=[
            SlotConstraint(pos=slot["pos"], kind=slot["kind"], value=slot.get("value"))
            for slot in query.slots
        ],
    )


def _compile_rhyme_anchor(query: RhymeAnchorQuery) -> CanonicalMatchSpec:
    mask = ["?"] * query.width
    if query.anchor_pos == 0:
        for pos, value in enumerate(query.slots, start=1):
            mask[pos] = value
    else:
        for pos, value in enumerate(query.slots):
            mask[pos] = value
    return finalize_canonical_match_spec(
        width=query.width,
        mask="".join(mask),
        slots=[
            SlotConstraint(
                pos=query.anchor_pos,
                kind="final_anchor" if query.constraint == "final" else "initial_anchor",
                value=query.anchor,
            )
        ],
    )


def _compile_triple_rhyme_anchor(query: TripleRhymeAnchorQuery) -> CanonicalMatchSpec:
    return finalize_canonical_match_spec(
        width=query.width,
        mask="?" * query.width,
        slots=[SlotConstraint(pos=query.anchor_pos, kind="final_anchor", value=query.anchor)],
    )


def _compile_mask(query: MaskQuery) -> CanonicalMatchSpec:
    return finalize_canonical_match_spec(
        width=len(query.raw_q),
        mask=query.raw_q,
        ranking="literal_priority",
        slots=[
            SlotConstraint(pos=pos, kind="code_digit", value=ch)
            for pos, ch in enumerate(query.raw_q)
            if ch.isdigit()
        ],
    )


def _code_prefix_slots(prefix: str | None) -> list[SlotConstraint]:
    if not prefix:
        return []
    return [SlotConstraint(pos=pos, kind="code_digit", value=value) for pos, value in enumerate(prefix)]


def _compile_wildcard_code_anchor(query: WildcardCodeAnchorQuery) -> CanonicalMatchSpec:
    mask = ["?"] * query.width
    slots = [
        SlotConstraint(pos=slot["pos"], kind=slot["kind"], value=slot.get("value"))
        for slot in query.slots
    ]
    for slot in slots:
        if slot.kind == "literal_char" and isinstance(slot.value, str):
            mask[slot.pos] = slot.value
    return finalize_canonical_match_spec(width=query.width, mask="".join(mask), slots=slots)


def _compile_compound(
    query: CompoundSynQuery
    | CompoundAntQuery
    | CompoundConnectSynQuery
    | CompoundConnectAntQuery,
    kind: str,
) -> CanonicalMatchSpec:
    width = 3 if query.kind in {QueryKind.COMPOUND_CONNECT_SYN, QueryKind.COMPOUND_CONNECT_ANT} else 2
    slots = _code_prefix_slots(query.code_prefix)
    if query.rhyme_char:
        slots.append(SlotConstraint(pos=width - 1, kind="final_anchor", value=query.rhyme_char))
    connective = getattr(query, "connective", None)
    return finalize_canonical_match_spec(
        width=width,
        slots=slots,
        compound_kind=kind,
        connective=connective,
    )


def _compile_doubled_syllable(query: CompoundDoubledSyllableQuery) -> CanonicalMatchSpec:
    slots = _code_prefix_slots(query.code_prefix)
    if query.rhyme_char:
        slots.append(SlotConstraint(pos=query.width - 1, kind="final_anchor", value=query.rhyme_char))
    return finalize_canonical_match_spec(
        width=query.width,
        slots=slots,
        compound_kind="doubled_syllable",
    )


def _jyutping_code_slots(query: JyutpingAnchorQuery) -> list[SlotConstraint]:
    if query.code_slots:
        return [
            SlotConstraint(pos=pos, kind="code_digit", value=value)
            for pos, value in query.code_slots
        ]
    if query.code_prefix and query.width == len(query.code_prefix):
        return _code_prefix_slots(query.code_prefix)
    return []


def _compile_jyutping_anchor(query: JyutpingAnchorQuery) -> CanonicalMatchSpec:
    code_slots = _jyutping_code_slots(query)
    if query.dual_phoneme:
        initial = finalize_canonical_match_spec(
            width=query.width,
            slots=[
                *code_slots,
                SlotConstraint(
                    pos=query.anchor_pos,
                    kind="initial_letters",
                    value=query.dual_initial_value or query.anchor_value,
                ),
            ],
        )
        final = finalize_canonical_match_spec(
            width=query.width,
            slots=[
                *code_slots,
                SlotConstraint(
                    pos=query.anchor_pos,
                    kind="rhyme_letters",
                    value=query.anchor_value,
                ),
            ],
        )
        return finalize_canonical_match_spec(
            width=query.width,
            slots=code_slots,
            phoneme_alternatives=CanonicalPhonemeAlternatives(initial, final),
        )
    return finalize_canonical_match_spec(
        width=query.width,
        slots=[
            *code_slots,
            SlotConstraint(pos=query.anchor_pos, kind=query.anchor_kind, value=query.anchor_value),
        ],
    )


def compile_parsed_query(parsed: ParsedQuery) -> CanonicalMatchSpec:
    return compile_query(require_match_spec_query(parsed))


MATCH_SPEC_QUERY_KINDS = frozenset(MATCH_SPEC_KINDS)


__all__ = [
    "MATCH_SPEC_QUERY_KINDS",
    "MatchSpecQuery",
    "compile_parsed_query",
    "compile_query",
    "require_match_spec_query",
]
