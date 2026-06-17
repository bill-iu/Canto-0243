"""Application startup orchestration (offline preload, lifespan hooks)."""

from app.startup.offline_preload import (
    get_readiness_snapshot,
    run_lifespan_startup,
)

__all__ = [
    "get_readiness_snapshot",
    "run_lifespan_startup",
]
