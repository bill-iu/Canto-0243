"""就緒閘 policy — CONTEXT § 就緒閘；ADR-0049 / ADR-0055."""

from __future__ import annotations

import os
import sys
import threading
from typing import Any, Callable

# DB probe literal — guide / offline contract
DB_PROBE_CHAR = "事業"

# word_cache dominates cold tail wall time — weight for honest badge progress
_WORD_CACHE_TAIL_WEIGHT = 0.72
_OTHER_TAIL_WEIGHT = 0.28

_lock = threading.Lock()
_db_probe_override: Callable[[], bool] | None = None


class SearchGateBlocked(Exception):
    """查詢分派在就緒閘未解鎖時拒絕搜尋。"""

    def __init__(self, snapshot: dict[str, Any]):
        self.snapshot = snapshot
        super().__init__("search gate not ready")


def reset_readiness_gate_for_tests() -> None:
    """測試用：清 probe override。"""
    global _db_probe_override
    with _lock:
        _db_probe_override = None


def set_db_probe_for_tests(fn: Callable[[], bool] | None) -> None:
    """測試注入 DB 探針（唔開真庫）。"""
    global _db_probe_override
    with _lock:
        _db_probe_override = fn


def _running_unittest_cli() -> bool:
    return any("unittest" in arg for arg in sys.argv)


def _enforcement_enabled() -> bool:
    raw = os.getenv("READINESS_GATE_ENFORCE")
    if raw is not None:
        return raw.lower() not in ("0", "false", "no")
    if _running_unittest_cli():
        return False
    return True


def _phase_done(snapshot: dict) -> bool:
    return snapshot.get("status") in ("ready", "failed")


def _db_searchable() -> bool:
    """詞條庫可查探針（ADR-0055）。"""
    with _lock:
        override = _db_probe_override
    if override is not None:
        try:
            return bool(override())
        except Exception:
            return False
    try:
        from app.database import SessionLocal
        from app.models.word import Word

        db = SessionLocal()
        try:
            row = (
                db.query(Word.id)
                .filter(Word.char == DB_PROBE_CHAR)
                .limit(1)
                .first()
            )
            return row is not None
        finally:
            db.close()
    except Exception:
        return False


def _collect_phases() -> tuple[dict, dict, dict, dict]:
    from app.startup.offline_preload import get_background_phase_snapshot
    from app.utils.word_cache import get_preload_snapshot

    return (
        get_preload_snapshot(),
        get_background_phase_snapshot("static_resources"),
        get_background_phase_snapshot("compound_syn"),
        get_background_phase_snapshot("compound_ant"),
    )


def _honest_tail_progress(word_cache: dict, others: tuple[dict, ...]) -> float:
    """Badge progress: heavy weight on word_cache so UI does not jump past indexing."""
    wc = max(0.0, min(1.0, float(word_cache.get("progress") or 0.0)))
    if others:
        o = sum(max(0.0, min(1.0, float(p.get("progress") or 0.0))) for p in others) / len(
            others
        )
    else:
        o = 1.0
    # If word_cache done, don't under-report other tail leftovers
    if word_cache.get("status") in ("ready", "failed"):
        return max(wc, o) if o < 1.0 else 1.0
    return _WORD_CACHE_TAIL_WEIGHT * wc + _OTHER_TAIL_WEIGHT * o


def snapshot() -> dict[str, Any]:
    """就緒閘契約：/ready 與 503 body 共用此 flat JSON。"""
    word_cache, static_resources, compound_syn, compound_ant = _collect_phases()
    other_tail = (static_resources, compound_syn, compound_ant)

    db_ready = _db_searchable()
    word_cache_ready = bool(word_cache.get("ready"))
    # ADR-0055: gate opens on DB probe — not full word_cache
    gate_ready = db_ready
    gate_open_reason = "ready" if db_ready else None
    degraded = False

    startup_complete = word_cache_ready and all(_phase_done(p) for p in other_tail)
    tail_pending = not startup_complete

    wc_status = word_cache.get("status") or "pending"
    status = wc_status
    if startup_complete:
        status = "ready"
    elif gate_ready and (wc_status == "loading" or any(p.get("status") == "loading" for p in other_tail)):
        status = "loading"
    elif not gate_ready:
        status = "pending"

    tail_progress = _honest_tail_progress(word_cache, other_tail)
    # Aggregate: pre-gate little weight; once open, mirror tail honesty
    if not gate_ready:
        aggregate_progress = 0.08 if not db_ready else 0.5
    else:
        aggregate_progress = 0.35 + 0.65 * tail_progress

    return {
        "gate_ready": gate_ready,
        "db_ready": db_ready,
        "degraded": degraded,
        "gate_open_reason": gate_open_reason,
        "ready": word_cache_ready,
        "startup_complete": startup_complete,
        "tail_pending": tail_pending,
        "status": status,
        "progress": aggregate_progress,
        "word_cache_progress": float(word_cache.get("progress") or 0.0),
        "tail_progress": tail_progress,
        "error": word_cache.get("error"),
        "phases": {
            "word_cache": word_cache,
            "static_resources": static_resources,
            "compound_syn": compound_syn,
            "compound_ant": compound_ant,
        },
    }


def require_search_ready() -> None:
    """查詢分派入口：閘未解鎖時拋 SearchGateBlocked（flat snapshot）。"""
    if not _enforcement_enabled():
        return
    snap = snapshot()
    if not snap["gate_ready"]:
        raise SearchGateBlocked(snap)


# Backward-compat name (deprecated for gate policy)
DEFAULT_DEGRADE_MS = 30_000


__all__ = [
    "DB_PROBE_CHAR",
    "DEFAULT_DEGRADE_MS",
    "SearchGateBlocked",
    "require_search_ready",
    "reset_readiness_gate_for_tests",
    "set_db_probe_for_tests",
    "snapshot",
]
