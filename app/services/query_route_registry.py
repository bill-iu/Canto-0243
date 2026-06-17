"""QueryKind → route classification（re-export；實作見 query_kind_registry）。"""
from __future__ import annotations

from app.services.query_kind_registry import (
    MASK_FAMILY_KINDS,
    RouteKind,
    route_kind_for,
)

__all__ = [
    "MASK_FAMILY_KINDS",
    "RouteKind",
    "route_kind_for",
]
