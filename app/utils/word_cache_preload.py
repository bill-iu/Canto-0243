"""詞庫快取預載 adapter — 背景載入編排與進度回報（Portable 就緒閘）。"""
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

# Honest continuous progress for badge (ADR-0055 tail):
# 0–0.05 restore try · 0.05–0.50 DB stream · 0.50–0.99 populate · 1.0 done
_DB_LOAD_BASE = 0.05
_DB_LOAD_SPAN = 0.45
_POPULATE_BASE = 0.50
_POPULATE_SPAN = 0.49
_DB_YIELD_EVERY = 1000


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


def _load_word_rows(db) -> list:
    """Stream words with progress so Portable gate does not stick at 15%."""
    from sqlalchemy import func

    from app.models.word import Word

    set_preload_progress(_DB_LOAD_BASE)
    total = (
        db.query(func.count())
        .select_from(Word)
        .filter(Word.length <= 10)
        .scalar()
    )
    total_n = int(total or 0)

    q = db.query(
        Word.char,
        Word.code,
        Word.jyutping,
        Word.finals,
        Word.initials,
        Word.length,
    ).filter(Word.length <= 10)

    rows: list = []
    # yield_per keeps memory bounded and allows progress ticks
    for i, row in enumerate(q.yield_per(_DB_YIELD_EVERY)):
        rows.append(row)
        if total_n > 0 and (i % _DB_YIELD_EVERY == 0 or i + 1 == total_n):
            frac = min(1.0, (i + 1) / total_n)
            set_preload_progress(_DB_LOAD_BASE + frac * _DB_LOAD_SPAN)
        elif total_n <= 0 and i > 0 and i % _DB_YIELD_EVERY == 0:
            # unknown count: soft log advance under populate base
            soft = min(_POPULATE_BASE - 0.01, _DB_LOAD_BASE + 0.08 * (1 + i // _DB_YIELD_EVERY))
            set_preload_progress(soft)

    set_preload_progress(_POPULATE_BASE)
    return rows


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

        begin_preload()
        try:
            if disk.disk_cache_enabled():
                set_preload_progress(0.05)
                if disk.try_restore(on_progress=set_preload_progress):
                    complete_preload()
                    print("[word_cache] restored from disk snapshot (.cache/word_meta.bin)")
                    return
                print("[word_cache] disk restore miss — cold build from SQLite")

            db = SessionLocal()
            try:
                rows = _load_word_rows(db)
            finally:
                db.close()

            populate_from_rows(rows)
            complete_preload()
            if disk.disk_cache_enabled():
                try:
                    disk.persist()
                    print("[word_cache] persisted disk snapshot for next warm start")
                except Exception as pe:
                    print(f"[word_cache] persist failed (next start will cold-build): {pe}")
        except Exception as e:
            fail_preload(str(e))
            print(
                "[word_cache] Word meta cache preload failed "
                "(mask/hybrid fall back to DB .all() + json per row): "
                f"{e}"
            )

    threading.Thread(target=_run, daemon=True).start()
