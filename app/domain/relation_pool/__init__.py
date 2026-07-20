"""近反義池 deep package (C7) — public surface is projection only (ADR-0050).

Import submodule symbols lazily so ranking/shim imports do not pull pool_builder
(and its derived_ant cycle) at package import time.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "PoolSnapshot",
    "project_relation_pool",
    "relation_chars_for_seed",
    "relation_pool_chars",
    "relation_pool_page",
]


def __getattr__(name: str) -> Any:
    if name in ("DEFAULT_PAGE_SIZE", "PoolSnapshot"):
        from app.domain.relation_pool.pool import DEFAULT_PAGE_SIZE, PoolSnapshot

        return {"DEFAULT_PAGE_SIZE": DEFAULT_PAGE_SIZE, "PoolSnapshot": PoolSnapshot}[name]
    if name in {
        "project_relation_pool",
        "relation_chars_for_seed",
        "relation_pool_chars",
        "relation_pool_page",
    }:
        from app.domain.relation_pool import pool_projection as _proj

        return getattr(_proj, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
