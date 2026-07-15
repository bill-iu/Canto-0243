"""AUTO-GENERATED from contracts/query-kind-manifest.json — do not edit.

Run: python scripts/codegen_query_kind_manifest.py
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

class QueryKind(str, Enum):
    """Parsed query classification (domain syntax types)."""

    RELATION_LOOKUP = "relation_lookup"
    COMPOUND_SYN = "compound_syn"
    COMPOUND_ANT = "compound_ant"
    COMPOUND_CONNECT_SYN = "compound_connect_syn"
    COMPOUND_CONNECT_ANT = "compound_connect_ant"
    COMPOUND_DOUBLED_SYLLABLE = "compound_doubled_syllable"
    HETERONYM_CODE = "heteronym_code"
    EQUALS = "equals"
    PREFIX_WILDCARD_EQUALS = "prefix_wildcard_equals"
    PARTIAL_RHYME_MASK = "partial_rhyme_mask"
    PARTIAL_INITIAL_MASK = "partial_initial_mask"
    SERIAL_PHONEME = "serial_phoneme"
    PLUS_ANCHOR = "plus_anchor"
    WILDCARD_CODE_ANCHOR = "wildcard_code_anchor"
    CODE_REF_MIDDLE_RHYME = "code_ref_middle_rhyme"
    LITERAL_REF = "literal_ref"
    RHYME_ANCHOR = "rhyme_anchor"
    TRIPLE_RHYME_ANCHOR = "triple_rhyme_anchor"
    JYUTPING_ANCHOR = "jyutping_anchor"
    MASK = "mask"
    PING_ZE_SERIAL = "ping_ze_serial"
    DIGIT_CODE = "digit_code"
    WORD_LOOKUP = "word_lookup"
    JYUTPING_FRAGMENT = "jyutping_fragment"
    UNMATCHED = "unmatched"


class RouteKind(str, Enum):
    DIGIT = "digit"
    MASK_FAMILY = "mask_family"
    HETERONYM = "heteronym"
    RELATION = "relation"
    LOOKUP = "lookup"
    UNMATCHED = "unmatched"
    EMPTY = "empty"


@dataclass(frozen=True)
class QueryKindMeta:
    route: RouteKind
    match_spec: bool = False


QUERY_KIND_META: dict[QueryKind, QueryKindMeta] = {
    QueryKind.RELATION_LOOKUP: QueryKindMeta(RouteKind.RELATION),
    QueryKind.COMPOUND_SYN: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.COMPOUND_ANT: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.COMPOUND_CONNECT_SYN: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.COMPOUND_CONNECT_ANT: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.COMPOUND_DOUBLED_SYLLABLE: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.HETERONYM_CODE: QueryKindMeta(RouteKind.HETERONYM),
    QueryKind.EQUALS: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PREFIX_WILDCARD_EQUALS: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PARTIAL_RHYME_MASK: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PARTIAL_INITIAL_MASK: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.SERIAL_PHONEME: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PLUS_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.WILDCARD_CODE_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.CODE_REF_MIDDLE_RHYME: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.LITERAL_REF: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.RHYME_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.TRIPLE_RHYME_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.JYUTPING_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.MASK: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PING_ZE_SERIAL: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.DIGIT_CODE: QueryKindMeta(RouteKind.DIGIT),
    QueryKind.WORD_LOOKUP: QueryKindMeta(RouteKind.LOOKUP),
    QueryKind.JYUTPING_FRAGMENT: QueryKindMeta(RouteKind.LOOKUP),
    QueryKind.UNMATCHED: QueryKindMeta(RouteKind.UNMATCHED),
}

MASK_FAMILY_KINDS: frozenset[QueryKind] = frozenset(
    k for k, m in QUERY_KIND_META.items() if m.route == RouteKind.MASK_FAMILY
)
MATCH_SPEC_KINDS: frozenset[QueryKind] = frozenset(
    k for k, m in QUERY_KIND_META.items() if m.match_spec
)


def route_kind_for(kind: QueryKind) -> RouteKind:
    meta = QUERY_KIND_META.get(kind)
    if meta is None:
        return RouteKind.EMPTY
    return meta.route


def uses_match_spec_kind(kind: QueryKind) -> bool:
    meta = QUERY_KIND_META.get(kind)
    if meta is None:
        return False
    return meta.match_spec


__all__ = [
    "MASK_FAMILY_KINDS",
    "MATCH_SPEC_KINDS",
    "QUERY_KIND_META",
    "QueryKind",
    "QueryKindMeta",
    "RouteKind",
    "route_kind_for",
    "uses_match_spec_kind",
]
