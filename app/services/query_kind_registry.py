"""QueryKind 元資料：route + MatchSpec（單一真相；ADR-0002）。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.services.query_types import QueryKind

if TYPE_CHECKING:
    from app.services.query_types import ParsedQuery


class RouteKind(str, Enum):
    DIGIT = "digit"
    MASK_FAMILY = "mask_family"
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
    QueryKind.HYBRID_TAIL_EQUALS_ALIAS: QueryKindMeta(RouteKind.MASK_FAMILY),
    QueryKind.EQUALS: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.PREFIX_WILDCARD_EQUALS: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.SERIAL_PHONEME: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.STAR_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.WILDCARD_CODE_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.CODE_REF_MIDDLE_RHYME: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.LITERAL_REF: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.RHYME_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.TRIPLE_RHYME_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.JYUTPING_ANCHOR: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.HYBRID_CODE: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
    QueryKind.MASK: QueryKindMeta(RouteKind.MASK_FAMILY, match_spec=True),
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


def uses_match_spec(parsed: "ParsedQuery") -> bool:
    """是否經 MatchSpec 進入缺字型查詢執行（含近義／反義複合）。"""
    meta = QUERY_KIND_META.get(parsed.kind)
    if meta is None:
        return False
    if meta.match_spec:
        return True
    return parsed.kind == QueryKind.HYBRID_TAIL_EQUALS_ALIAS


__all__ = [
    "MASK_FAMILY_KINDS",
    "MATCH_SPEC_KINDS",
    "QUERY_KIND_META",
    "QueryKindMeta",
    "RouteKind",
    "route_kind_for",
    "uses_match_spec",
]
