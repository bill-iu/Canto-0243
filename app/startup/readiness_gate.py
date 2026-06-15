"""就緒閘 policy — CONTEXT § 就緒閘、降級逾時；ADR-0001."""

from __future__ import annotations

import os
import sys
import time
import threading
from typing import Any

DEFAULT_DEGRADE_MS = 30_000

_lock = threading.Lock()
_loading_started_at: float | None = None


class SearchGateBlocked(Exception):
    """查詢分派在就緒閘未解鎖時拒絕搜尋。"""

    def __init__(self, snapshot: dict[str, Any]):
        self.snapshot = snapshot
        super().__init__("search gate not ready")


def reset_readiness_gate_for_tests() -> None:
    """測試用：重設降級逾時起算。"""
    global _loading_started_at
    with _lock:
        _loading_started_at = None


def _running_unittest_cli() -> bool:
    return any("unittest" in arg for arg in sys.argv)


def _enforcement_enabled() -> bool:
    raw = os.getenv("READINESS_GATE_ENFORCE")
    if raw is not None:
        return raw.lower() not in ("0", "false", "no")
    if _running_unittest_cli():
        return False
    return True


def _degrade_timeout_ms() -> int:
    raw = os.getenv("GATE_DEGRADE_MS", str(DEFAULT_DEGRADE_MS))
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_DEGRADE_MS


def _phase_done(snapshot: dict) -> bool:
    return snapshot.get("status") in ("ready", "failed")


def _collect_phases() -> tuple[dict, dict, dict]:
    from app.startup.offline_preload import get_background_phase_snapshot
    from app.utils.word_cache import get_preload_snapshot

    return (
        get_preload_snapshot(),
        get_background_phase_snapshot("static_resources"),
        get_background_phase_snapshot("compound_syn"),
    )


def _sync_loading_clock(wc_status: str) -> None:
    global _loading_started_at
    with _lock:
        if wc_status == "loading":
            if _loading_started_at is None:
                _loading_started_at = time.monotonic()
        elif wc_status in ("ready", "failed", "pending"):
            _loading_started_at = None


def _gate_open_reason(word_cache: dict) -> str | None:
    wc_status = word_cache.get("status") or "pending"
    if wc_status == "ready":
        return "ready"
    if wc_status == "failed":
        return "failed"
    if wc_status == "loading":
        timeout_s = _degrade_timeout_ms() / 1000.0
        with _lock:
            started = _loading_started_at
        if started is not None and timeout_s > 0 and time.monotonic() - started >= timeout_s:
            return "degraded"
    return None


def snapshot() -> dict[str, Any]:
    """就緒閘契約：/ready 與 503 body 共用此 flat JSON。"""
    word_cache, static_resources, compound_syn = _collect_phases()
    wc_status = word_cache.get("status") or "pending"
    _sync_loading_clock(wc_status)

    phases = [word_cache, static_resources, compound_syn]
    aggregate_progress = sum(float(p.get("progress") or 0.0) for p in phases) / 3.0
    tail_progress = (
        float(static_resources.get("progress") or 0.0) + float(compound_syn.get("progress") or 0.0)
    ) / 2.0

    word_cache_ready = bool(word_cache.get("ready"))
    gate_open_reason = _gate_open_reason(word_cache)
    gate_ready = gate_open_reason is not None
    degraded = gate_open_reason == "degraded"
    startup_complete = word_cache_ready and all(_phase_done(p) for p in (static_resources, compound_syn))
    tail_pending = not all(_phase_done(p) for p in (static_resources, compound_syn))

    status = wc_status
    if startup_complete:
        status = "ready"
    elif status == "pending" and any(
        p.get("status") == "loading" for p in (static_resources, compound_syn)
    ):
        status = "loading"

    return {
        "gate_ready": gate_ready,
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
        },
    }


def require_search_ready() -> None:
    """查詢分派入口：閘未解鎖時拋 SearchGateBlocked（flat snapshot）。"""
    if not _enforcement_enabled():
        return
    snap = snapshot()
    if not snap["gate_ready"]:
        raise SearchGateBlocked(snap)


__all__ = [
    "DEFAULT_DEGRADE_MS",
    "SearchGateBlocked",
    "require_search_ready",
    "reset_readiness_gate_for_tests",
    "snapshot",
]
