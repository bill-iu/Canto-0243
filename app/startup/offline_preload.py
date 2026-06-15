"""離線啟動預載 — CONTEXT § 就緒閘、離線啟動預載。"""

from __future__ import annotations

import os
import threading
from typing import Callable

from app.database import Base, IS_POSTGRES, SessionLocal, engine

_startup_lock = threading.Lock()
_background_started = False
_background_state = {
    "static_resources": {"status": "pending", "progress": 0.0, "error": None},
    "compound_syn": {"status": "pending", "progress": 0.0, "error": None},
}


def _local_sqlite_startup_enabled(env: str) -> bool:
    return (env != "prod" and not IS_POSTGRES) or bool(os.getenv("FORCE_CREATE_ALL"))


def reset_background_preload_state_for_tests() -> None:
    """測試用：重設背景預載狀態。"""
    global _background_started
    with _startup_lock:
        _background_started = False
        for key in _background_state:
            _background_state[key] = {"status": "pending", "progress": 0.0, "error": None}


def _set_background_phase(
    phase: str,
    *,
    status: str | None = None,
    progress: float | None = None,
    error: str | None = None,
) -> None:
    with _startup_lock:
        slot = _background_state[phase]
        if status is not None:
            slot["status"] = status
        if progress is not None:
            slot["progress"] = progress
        if error is not None:
            slot["error"] = error


def ensure_dev_length_schema() -> None:
    """Lifespan：本地 SQLite length 欄位輕量 ensure。"""
    try:
        from app.db.bootstrap import ensure_length_column

        ensure_length_column()
    except Exception:
        pass


def start_background_word_cache_preload() -> None:
    """背景載入 word_cache（就緒閘搜尋解鎖依據）。"""
    from app.utils.word_cache import start_word_cache_preload_background

    start_word_cache_preload_background()


def run_create_all_if_needed(env: str) -> None:
    if not _local_sqlite_startup_enabled(env):
        print("[offline_preload] 略過 create_all（正式環境建議使用 alembic upgrade head）")
        return
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[offline_preload] ⚠️ create_all 失敗（很可能是 database is locked）：{e}")
        print("[offline_preload] 建議：關閉所有其他 python / uvicorn / backfill 程序後再試。")
        print("[offline_preload] 應用程式仍會繼續啟動（假設表格已存在）。")


def run_local_db_bootstrap(env: str) -> None:
    if not _local_sqlite_startup_enabled(env):
        return
    try:
        from app.db.bootstrap import bootstrap_local_db

        bootstrap_local_db()
    except Exception as e:
        print(f"[offline_preload] schema ensure / length backfill 啟動失敗（可忽略）：{e}")


def _best_effort(label: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        print(f"[offline_preload] {label} 已載入。")
    except Exception as e:
        print(f"[offline_preload] {label} preload 失敗（可忽略）：{e}")


def preload_static_runtime_resources() -> None:
    """載入靜態詞林、排序語料等。"""
    from app.lexicon.curated_index import ensure_curated_loaded
    from app.lexicon.essay_index import ensure_essay_loaded
    from app.lexicon.rime_char_index import ensure_rime_char_loaded
    from app.lexicon.static_index import ensure_lexicon_loaded
    from app.thesaurus.static_index import ensure_thesaurus_loaded

    _best_effort("Static thesaurus (cilin / antonym / thesaurus)", ensure_thesaurus_loaded)
    _best_effort("詞級標音詞庫（maintainer 匯入 JSON）", ensure_lexicon_loaded)
    _best_effort("Rime char.csv lexicon (data/rime/char.csv)", ensure_rime_char_loaded)
    _best_effort("Essay frequency corpus (data/essay/essay-cantonese.txt)", ensure_essay_loaded)
    _best_effort("Curated common words (data/lexicon/curated_common.txt)", ensure_curated_loaded)


def preload_compound_syn_runtime_cache() -> None:
    from app.domain.relations.compound_syn import ensure_compound_syn_snapshot

    def _run() -> None:
        db = SessionLocal()
        try:
            ensure_compound_syn_snapshot(db)
        finally:
            db.close()

    _best_effort("近義複合（~~）快照", _run)


def _run_background_phase(phase: str, fn: Callable[[], None]) -> None:
    _set_background_phase(phase, status="loading", progress=0.05)
    try:
        fn()
        _set_background_phase(phase, status="ready", progress=1.0)
    except Exception as e:
        _set_background_phase(phase, status="failed", progress=1.0, error=str(e))


def start_background_runtime_preload() -> None:
    """lifespan：詞庫快取、靜態語料、複合詞快取並行背景預載。"""
    global _background_started
    with _startup_lock:
        if _background_started:
            return
        _background_started = True

    try:
        start_background_word_cache_preload()
    except Exception as e:
        print(f"[offline_preload] Word cache preload thread failed to start: {e}")

    threading.Thread(
        target=_run_background_phase,
        args=("static_resources", preload_static_runtime_resources),
        daemon=True,
    ).start()
    threading.Thread(
        target=_run_background_phase,
        args=("compound_syn", preload_compound_syn_runtime_cache),
        daemon=True,
    ).start()


def run_lifespan_startup(*, env: str | None = None) -> None:
    """FastAPI lifespan：schema ensure + 背景預載（uvicorn worker 內執行）。"""
    effective_env = (env or os.getenv("ENV", "local")).lower()
    if _local_sqlite_startup_enabled(effective_env):
        run_create_all_if_needed(effective_env)
        run_local_db_bootstrap(effective_env)
        ensure_dev_length_schema()
    start_background_runtime_preload()


def run_main_block_startup(*, env: str | None = None) -> None:
    """`python main.py`：僅 DB ensure；其餘預載交 lifespan 背景。"""
    effective_env = (env or os.getenv("ENV", "local")).lower()
    run_create_all_if_needed(effective_env)
    run_local_db_bootstrap(effective_env)


def _phase_snapshot(phase: str) -> dict:
    with _startup_lock:
        slot = _background_state[phase]
        return {
            "status": slot["status"],
            "progress": float(slot["progress"]),
            "error": slot["error"],
        }


def get_background_phase_snapshot(phase: str) -> dict:
    """背景預載 phase 快照（供 readiness_gate 消費）。"""
    return _phase_snapshot(phase)


def get_readiness_snapshot() -> dict:
    """就緒閘 API：委派 readiness_gate.snapshot()。"""
    from app.startup.readiness_gate import snapshot

    return snapshot()


__all__ = [
    "get_background_phase_snapshot",
    "get_readiness_snapshot",
    "reset_background_preload_state_for_tests",
    "run_lifespan_startup",
    "run_main_block_startup",
    "start_background_runtime_preload",
    "start_background_word_cache_preload",
    "preload_static_runtime_resources",
    "preload_compound_syn_runtime_cache",
]
