"""查詢種類 → MatchSpec builders（CONTEXT § 查詢種類；ADR-0002 Phase 1）。"""
from __future__ import annotations

from typing import Callable, Optional

from app.services.jyutping_anchor import (
    build_jyutping_dual_match_specs,
    to_match_spec as jyutping_to_match_spec,
)
from app.services.position_match import MatchSpec
from app.services.query_types import ParsedQuery, QueryKind


MatchSpecBuilder = Callable[[ParsedQuery], Optional[MatchSpec]]


def _spec_equals(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.equals import to_match_spec as equals_to_match_spec

    return equals_to_match_spec(parsed)


def _spec_serial(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.serial import to_match_spec as serial_to_match_spec

    return serial_to_match_spec(parsed)


def _spec_rhyme(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.rhyme import to_match_spec as rhyme_to_match_spec

    return rhyme_to_match_spec(parsed)


def _spec_plus(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.plus import to_match_spec as plus_to_match_spec

    return plus_to_match_spec(parsed)


def _spec_mask(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.mask import to_match_spec as mask_to_match_spec

    return mask_to_match_spec(parsed)


def _spec_wca(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.wca import to_match_spec as wca_to_match_spec

    return wca_to_match_spec(parsed)


def _spec_jyutping_anchor(parsed: ParsedQuery) -> Optional[MatchSpec]:
    return jyutping_to_match_spec(parsed)


def _spec_ping_ze_serial(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.ping_zak import to_match_spec as pingze_to_match_spec

    return pingze_to_match_spec(parsed)


def _spec_relation(parsed: ParsedQuery) -> Optional[MatchSpec]:
    from app.services.query_grammar.relation import to_match_spec as relation_to_match_spec

    return relation_to_match_spec(parsed)


MATCH_SPEC_BUILDERS: dict[QueryKind, MatchSpecBuilder] = {
    QueryKind.EQUALS: _spec_equals,
    QueryKind.PREFIX_WILDCARD_EQUALS: _spec_serial,
    QueryKind.PARTIAL_RHYME_MASK: _spec_rhyme,
    QueryKind.PARTIAL_INITIAL_MASK: _spec_rhyme,
    QueryKind.SERIAL_PHONEME: _spec_serial,
    QueryKind.PLUS_ANCHOR: _spec_plus,
    QueryKind.LITERAL_REF: _spec_plus,
    QueryKind.WILDCARD_CODE_ANCHOR: _spec_wca,
    QueryKind.CODE_REF_MIDDLE_RHYME: _spec_rhyme,
    QueryKind.RHYME_ANCHOR: _spec_rhyme,
    QueryKind.TRIPLE_RHYME_ANCHOR: _spec_rhyme,
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


__all__ = [
    "MATCH_SPEC_BUILDERS",
    "MatchSpecBuilder",
    "build_jyutping_dual_match_specs",
    "build_match_spec_for_parsed",
]
