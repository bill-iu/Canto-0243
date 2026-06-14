"""離線啟動預載 — CONTEXT § 就緒閘、離線啟動預載。"""

from __future__ import annotations

import os
from typing import Callable

from app.database import Base, IS_POSTGRES, SessionLocal, engine


def _local_sqlite_startup_enabled(env: str) -> bool:
    return (env != "prod" and not IS_POSTGRES) or bool(os.getenv("FORCE_CREATE_ALL"))


def ensure_dev_length_schema() -> None:
    """Lifespan：本地 SQLite length 欄位輕量 ensure。"""
    try:
        from app.db.bootstrap import ensure_length_column

        ensure_length_column()
    except Exception:
        pass


def start_background_word_cache_preload() -> None:
    """背景載入 word_cache（就緒閘 /ready 資料來源）。"""
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
    """Eager 載入靜態詞林、排序語料等（`python main.py` 路徑）。"""
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
    from app.domain.relations.compound_syn import ensure_compound_syn_cache

    def _run() -> None:
        db = SessionLocal()
        try:
            ensure_compound_syn_cache(db)
        finally:
            db.close()

    _best_effort("近義複合（~~）字面快取", _run)


def run_lifespan_startup(*, env: str | None = None) -> None:
    """FastAPI lifespan：schema ensure + word_cache 背景預載。"""
    effective_env = (env or os.getenv("ENV", "local")).lower()
    if _local_sqlite_startup_enabled(effective_env):
        ensure_dev_length_schema()
    try:
        start_background_word_cache_preload()
    except Exception as e:
        print(f"[offline_preload] Word cache preload thread failed to start: {e}")


def run_main_block_startup(*, env: str | None = None) -> None:
    """`python main.py`：create_all、bootstrap、靜態資源與複合詞快取 eager preload。"""
    effective_env = (env or os.getenv("ENV", "local")).lower()
    run_create_all_if_needed(effective_env)
    run_local_db_bootstrap(effective_env)
    preload_static_runtime_resources()
    preload_compound_syn_runtime_cache()


def get_readiness_snapshot() -> dict:
    """就緒閘 API 快照（詞庫 word_cache）。"""
    from app.utils.word_cache import get_preload_snapshot

    return get_preload_snapshot()


__all__ = [
    "get_readiness_snapshot",
    "run_lifespan_startup",
    "run_main_block_startup",
    "start_background_word_cache_preload",
    "preload_static_runtime_resources",
    "preload_compound_syn_runtime_cache",
]
