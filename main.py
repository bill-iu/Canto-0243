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
            from app.database import ensure_length_column
            ensure_length_column()
        except Exception:
            pass  # 失敗不影響啟動，有 fallback
        # Warmup embedding in background (non-blocking now).
        # The actual model load happens in a daemon thread; first requests get fast fallback.
        try:
            import threading
            from utils import get_text_embedding
            def _warmup():
                try:
                    get_text_embedding("暖機")
                except Exception:
                    pass
            threading.Thread(target=_warmup, daemon=True).start()
        except Exception:
            pass
    yield

app = FastAPI(title="0243 押韻字典", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
            from app.database import ensure_length_column, start_length_backfill
            ensure_length_column()          # 輕量：只 ALTER + 建 index（如果需要）
            start_length_backfill()         # 重型 backfill 會在 daemon thread 啟動，不阻塞 uvicorn.run
        except Exception as e:
            print(f"[main] length schema / backfill 啟動失敗（可忽略，搜尋有 fallback）：{e}")

    # Warmup embedding model in background thread.
    # IMPORTANT: get_text_embedding is now non-blocking on first call.
    # It immediately returns [] and starts a background thread to load the model.
    # This means: the server is responsive instantly after "python main.py".
    # Basic searches (code, digit, jyutping, canto without semantic, syn static) work right away.
    # Vector semantic (re-rank + syn vector blend) becomes available after the model finishes loading (a few seconds).
    # You will see "[embedding] ... 已就緒" in the console when it's ready.
    try:
        import threading
        from utils import get_text_embedding
        def _warmup_embedding():
            try:
                get_text_embedding("暖機")  # this call is now instant (just kicks the loader)
            except Exception:
                pass
        threading.Thread(target=_warmup_embedding, daemon=True).start()
    except Exception:
        pass

    # Preload full embedding matrix (for syn/ant vectorized top-k / low-sim) + static thesaurus indices.
    # Done in explicit __main__ (same as length/embedding) so uvicorn --reload child processes stay clean.
    # Safe if no embeddings or no data files (syn mode falls back gracefully).
    try:
        import threading
        import numpy as np
        from app.database import SessionLocal
        from app.models.word import Word
        from utils import (
            load_json_list,
            set_synonym_index,
            load_cilin_index,
            load_antonym_dict,
            load_thesaurus_dicts,
        )

        def _preload_syn_index():
            try:
                db = SessionLocal()
                try:
                    rows = (
                        db.query(Word.char, Word.embedding)
                        .filter(Word.embedding.isnot(None))
                        .filter(Word.embedding != "")
                        .all()
                    )
                finally:
                    db.close()

                chars = []
                vecs = []
                for char, emb in rows:
                    if not char:
                        continue
                    v = load_json_list(emb)
                    if isinstance(v, list) and len(v) == 384:
                        chars.append(char)
                        vecs.append(v)

                if not chars or not vecs:
                    print("[main] Synonym index preload: no embeddings found (syn mode will use static-only fallback).")
                    # Still attempt static loads
                    try:
                        load_cilin_index()
                        load_antonym_dict()
                        load_thesaurus_dicts()
                    except Exception:
                        pass
                    return

                mat = np.asarray(vecs, dtype=np.float32)
                # Row-normalize (so dot == cosine)
                norms = np.linalg.norm(mat, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                mat = mat / norms

                set_synonym_index(chars, mat)

                # Static curated (non-fatal if files absent)
                try:
                    load_cilin_index()
                    load_antonym_dict()
                    load_thesaurus_dicts()
                except Exception:
                    pass

                print(f"[main] Synonym/antonym index preloaded: {len(chars)} entries (matrix ready for instant syn mode).")
            except Exception as e:
                print(f"[main] Synonym index preload failed (syn mode falls back to static/emb-per-query): {e}")

        threading.Thread(target=_preload_syn_index, daemon=True).start()
    except Exception:
        pass

    # Preload short-word metadata cache (for instant mask/hybrid/"門0"/"好23"/wildcard paths).
    # Query minimal columns, pre-parse JSON finals etc ONCE at startup (no per-request json.loads).
    # Uses populate (not full query inside utils) to stay consistent with _preload_syn_index and avoid import cycles.
    # New words injected by _ensure are synced via update_word_in_cache so they participate without restart.
    # Fallback in router: if buckets empty, still does the old DB path (correctness first).
    try:
        import threading
        from app.database import SessionLocal
        from app.models.word import Word
        from utils import populate_word_cache_from_rows, get_word_cache_stats

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
        reload=os.getenv("ENV", "local").lower() != "prod",
    )