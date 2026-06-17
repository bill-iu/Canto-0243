"""QueryKind → route classification（ADR-0002 Phase 2）。"""
from __future__ import annotations

from enum import Enum

from app.services.query_parse import QueryKind


class RouteKind(str, Enum):
    DIGIT = "digit"
    MASK_FAMILY = "mask_family"
    RELATION = "relation"
    LOOKUP = "lookup"
    UNMATCHED = "unmatched"
    EMPTY = "empty"


MASK_FAMILY_KINDS: frozenset[QueryKind] = frozenset(
    {
        QueryKind.HYBRID_TAIL_EQUALS_ALIAS,
        QueryKind.EQUALS,
        QueryKind.PREFIX_WILDCARD_EQUALS,
        QueryKind.SERIAL_PHONEME,
        QueryKind.STAR_ANCHOR,
        QueryKind.WILDCARD_CODE_ANCHOR,
        QueryKind.CODE_REF_MIDDLE_RHYME,
        QueryKind.LITERAL_REF,
        QueryKind.RHYME_ANCHOR,
        QueryKind.TRIPLE_RHYME_ANCHOR,
        QueryKind.JYUTPING_ANCHOR,
        QueryKind.HYBRID_CODE,
        QueryKind.MASK,
        QueryKind.COMPOUND_SYN,
        QueryKind.COMPOUND_ANT,
    }
)


def route_kind_for(kind: QueryKind) -> RouteKind:
    if kind == QueryKind.DIGIT_CODE:
        return RouteKind.DIGIT
    if kind in MASK_FAMILY_KINDS:
        return RouteKind.MASK_FAMILY
    if kind == QueryKind.RELATION_LOOKUP:
        return RouteKind.RELATION
    if kind in (QueryKind.WORD_LOOKUP, QueryKind.JYUTPING_FRAGMENT):
        return RouteKind.LOOKUP
    if kind == QueryKind.UNMATCHED:
        return RouteKind.UNMATCHED
    return RouteKind.EMPTY


__all__ = [
    "MASK_FAMILY_KINDS",
    "RouteKind",
    "route_kind_for",
]

