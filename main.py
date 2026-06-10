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
        # Warmup embedding in background to avoid load delay on first hanzi search
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

    # Warmup embedding model in background thread for instant first hanzi/click search (model load + encode is ~1-2s otherwise)
    try:
        import threading
        from utils import get_text_embedding
        def _warmup_embedding():
            try:
                get_text_embedding("暖機")
                print("[main] Embedding model warmed up for instant semantic results.")
            except Exception:
                pass  # non-fatal
        threading.Thread(target=_warmup_embedding, daemon=True).start()
    except Exception:
        pass

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "local").lower() != "prod",
    )