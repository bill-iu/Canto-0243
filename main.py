import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, IS_POSTGRES
from app.routers.word import router

# 輕量 lifespan：確保 schema（例如 length 欄位），但不啟動重型 backfill。
# 重型 backfill 仍由 __main__ 明確啟動（避免 reload child process 自動做重工）。
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if (os.getenv("ENV", "local").lower() != "prod" and not IS_POSTGRES):
        try:
            from app.db.bootstrap import ensure_length_column

            ensure_length_column()
        except Exception:
            pass  # 失敗不影響啟動，有 fallback
    yield

app = FastAPI(title="0243 押韻字典", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Tightened for safety: in production prefer explicit origins (e.g. via env).
    # Current default keeps local dev convenience for the offline lyrics tool.
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")
app.include_router(router)


@app.get("/")
async def home():
    return {
        "status": "running",
        "portable": bool(os.getenv("PORTABLE")),
        "frontend": "http://127.0.0.1:8000/frontend/index.html",
        "api_test": "http://127.0.0.1:8000/words/search/?q=23",
    }


if __name__ == "__main__":
    # 僅在本地 / SQLite 時自動 create_all（正式 PostgreSQL 請使用 Alembic）
    env = os.getenv("ENV", "local").lower()
    if (env != "prod" and not IS_POSTGRES) or os.getenv("FORCE_CREATE_ALL"):
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            # 常見原因：另一個 python 程序（例如 backfill_embeddings.py、其他 uvicorn、搜尋測試）還在持有 lyrics.db 的鎖。
            # SQLite 單一 writer 限制。在 Windows 上特別容易發生。
            # 解決：關閉其他使用該 DB 的 python 程序、等 backfill 完全結束、或重啟終端機。
            # 因為表格通常已存在，繼續啟動通常沒問題（auto ALTER 會在下次乾淨啟動時補欄位）。
            print(f"[main] ⚠️ create_all 失敗（很可能是 database is locked）：{e}")
            print("[main] 建議：關閉所有其他 python / uvicorn / backfill 程序後再試。")
            print("[main] 應用程式仍會繼續啟動（假設表格已存在）。")
    else:
        print("[main] 略過 create_all（正式環境建議使用 alembic upgrade head）")

    # === 一次解決 reload / spawn 問題的核心呼叫 ===
    # 這些函式只在明確的 __main__ 路徑執行，不會在 uvicorn reload 的 child process import 時自動觸發。
    # 這樣 import database 時完全沒有副作用，StatReload 穩定。
    if (env != "prod" and not IS_POSTGRES) or os.getenv("FORCE_CREATE_ALL"):
        try:
            from app.db.bootstrap import bootstrap_local_db

            bootstrap_local_db()
        except Exception as e:
            print(f"[main] schema ensure / length backfill 啟動失敗（可忽略）：{e}")

    # === Embedding model load completely disabled at runtime (redesign complete) ===
    # Per user request and previous plan: the MiniLM model is ONLY loaded inside
    # generate_relationships.py (ingest/dev-only script).
    # Normal `python main.py` or uvicorn will NEVER trigger the background load
    # or print the "[embedding] 正在背景載入 ..." message, even if sentence-transformers
    # happens to be importable in the current environment.
    #
    # All syn/ant functionality now uses precomputed word_relations + static thesaurus.
    # Semantic features (if any) must come from pre-generated data only.

    # === Synonym/Antonym 預載（以 SQL relations + static thesaurus 為主）===
    # 目標：一般使用者不需要 sentence-transformers / torch。
    # 現在 syn/ant 主要來源是 word_relations 表（generate_relationships.py 在 ingest 時產生）+ static thesaurus。
    # 舊的 embedding matrix preload 邏輯已完全移除，不再於 runtime 執行。
    try:
        from app.thesaurus.static_index import ensure_thesaurus_loaded
        ensure_thesaurus_loaded()
        print("[main] Static thesaurus (cilin / antonym / thesaurus) 已載入。")
    except Exception as e:
        print(f"[main] Static thesaurus preload 失敗（可忽略）：{e}")

    try:
        from app.lexicon.static_index import ensure_lexicon_loaded

        ensure_lexicon_loaded()
        print("[main] Static 0243 lexicon (data/raw/clean) 已載入。")
    except Exception as e:
        print(f"[main] Lexicon preload 失敗（可忽略）：{e}")

    try:
        from app.lexicon.rime_char_index import ensure_rime_char_loaded

        ensure_rime_char_loaded()
        print("[main] Rime char.csv lexicon (data/rime/char.csv) 已載入。")
    except Exception as e:
        print(f"[main] Rime char preload 失敗（可忽略）：{e}")

    try:
        from app.lexicon.essay_index import ensure_essay_loaded

        ensure_essay_loaded()
        print("[main] Essay frequency corpus (data/essay/essay-cantonese.txt) 已載入。")
    except Exception as e:
        print(f"[main] Essay corpus preload 失敗（可忽略）：{e}")

    try:
        from app.lexicon.curated_index import ensure_curated_loaded

        ensure_curated_loaded()
        print("[main] Curated common words (data/lexicon/curated_common.txt) 已載入。")
    except Exception as e:
        print(f"[main] Curated lexicon preload 失敗（可忽略）：{e}")

    # Preload short-word metadata cache (for instant mask/hybrid/"門0"/"好23"/wildcard paths).
    # Query minimal columns, pre-parse JSON finals etc ONCE at startup (no per-request json.loads).
    # New words injected by _ensure are synced via update_word_in_cache so they participate without restart.
    # Fallback in router: if buckets empty, still does the old DB path (correctness first).
    # Note: This is independent of the embedding model (which is ingest-only).
    try:
        import threading
        from app.database import SessionLocal
        from app.models.word import Word
        from app.utils.word_cache import get_word_cache_stats, populate_word_cache_from_rows

        def _preload_word_cache():
            try:
                db = SessionLocal()
                try:
                    # Only need fields used by mask/hybrid position matching + priority + display.
                    # We intentionally limit to short words (lyrics-style patterns are almost always N<=8).
                    # This makes preload much lighter + reduces SQLite lock contention risk at startup.
                    # Long-word mask/hybrid cases (very rare) will transparently fall back to the DB path.
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

                n = populate_word_cache_from_rows(rows)
                stats = get_word_cache_stats()
                print(f"[main] Word meta cache preloaded: {n} entries (lengths={stats['lengths'][:8]}... total_meta={stats['meta_size']}). Mask/hybrid now use pre-parsed in-mem (instant).")
            except Exception as e:
                print(f"[main] Word meta cache preload failed (mask/hybrid fall back to DB .all() + json per row): {e}")

        threading.Thread(target=_preload_word_cache, daemon=True).start()
    except Exception:
        pass

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "local").lower() != "prod" and not os.getenv("PORTABLE"),
    )