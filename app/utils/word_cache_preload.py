"""詞庫快取預載 adapter — 背景載入編排與進度回報。"""
from __future__ import annotations

import threading
from typing import Callable

from app.utils import word_cache_disk as disk
from app.utils import word_cache_index as index

_preload_lock = threading.Lock()
_preload_start_lock = threading.Lock()
_preload_thread_started = False
_preload_state = {
    "status": "pending",
    "progress": 0.0,
    "error": None,
}

_POPULATE_BASE = 0.55
_POPULATE_SPAN = 0.44


def _set_status(*, status: str | None = None, progress: float | None = None, error: str | None = None) -> None:
    with _preload_lock:
        if status is not None:
            _preload_state["status"] = status
        if progress is not None:
            _preload_state["progress"] = progress
        if error is not None:
            _preload_state["error"] = error


def set_preload_progress(progress: float) -> None:
    _set_status(progress=progress)


def begin_preload() -> None:
    _set_status(status="loading", progress=0.0, error=None)


def complete_preload() -> None:
    _set_status(status="ready", progress=1.0, error=None)


def fail_preload(message: str) -> None:
    _set_status(status="failed", error=message)


def get_preload_snapshot() -> dict:
    with _preload_lock:
        status = _preload_state["status"]
        return {
            "ready": status == "ready" and index.is_populated(),
            "status": status,
            "progress": float(_preload_state["progress"]),
            "error": _preload_state["error"],
        }


def is_preload_complete() -> bool:
    with _preload_lock:
        return _preload_state["status"] == "ready"


def _populate_progress_callback() -> Callable[[float], None]:
    def on_progress(frac: float) -> None:
        with _preload_lock:
            if _preload_state["status"] != "loading":
                return
        set_preload_progress(_POPULATE_BASE + frac * _POPULATE_SPAN)

    return on_progress


def populate_from_rows(rows: list) -> int:
    return index.populate_from_rows(rows, on_progress=_populate_progress_callback())


def reset_preload_for_tests() -> None:
    global _preload_thread_started
    _preload_thread_started = False
    with _preload_lock:
        _preload_state["status"] = "pending"
        _preload_state["progress"] = 0.0
        _preload_state["error"] = None


def start_background_preload() -> None:
    """Start word-cache preload in the current process (uvicorn worker / lifespan)."""
    global _preload_thread_started
    with _preload_start_lock:
        with _preload_lock:
            if _preload_thread_started or _preload_state["status"] in ("loading", "ready"):
                return
        _preload_thread_started = True

    def _run() -> None:
        from app.database import SessionLocal
        from app.models.word import Word

        begin_preload()
        try:
            if disk.disk_cache_enabled() and disk.try_restore(on_progress=set_preload_progress):
                complete_preload()
                return

            db = SessionLocal()
            try:
                set_preload_progress(0.15)
                rows = (
                    db.query(
                        Word.char,
                        Word.code,
                        Word.jyutping,
                        Word.finals,
                        Word.initials,
                        Word.length,
                    )
                    .filter(Word.length <= 10)
                    .all()
                )
            finally:
                db.close()

            set_preload_progress(_POPULATE_BASE)
            populate_from_rows(rows)
            complete_preload()
            if disk.disk_cache_enabled():
                disk.persist()
        except Exception as e:
            fail_preload(str(e))
            print(
                "[word_cache] Word meta cache preload failed "
                "(mask/hybrid fall back to DB .all() + json per row): "
                f"{e}"
            )

    threading.Thread(target=_run, daemon=True).start()
