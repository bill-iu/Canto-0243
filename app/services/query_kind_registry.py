"""QueryKind 元資料 facade — re-export generated SSOT (ADR-0035)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.services._generated.query_kind_registry import (
    MASK_FAMILY_KINDS,
    MATCH_SPEC_KINDS,
    QUERY_KIND_META,
    QueryKind,
    QueryKindMeta,
    RouteKind,
    route_kind_for,
    uses_match_spec_kind,
)

if TYPE_CHECKING:
    from app.services.query_types import ParsedQuery


def uses_match_spec(parsed: "ParsedQuery") -> bool:
    """是否經 MatchSpec 進入缺字型查詢執行（含近義／反義複合）。"""
    return uses_match_spec_kind(parsed.kind)


__all__ = [
    "MASK_FAMILY_KINDS",
    "MATCH_SPEC_KINDS",
    "QUERY_KIND_META",
    "QueryKind",
    "QueryKindMeta",
    "RouteKind",
    "route_kind_for",
    "uses_match_spec",
    "uses_match_spec_kind",
]
