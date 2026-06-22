import os

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from app.routers.lexicon import router as lexicon_router
from app.routers.relation import router as relation_router
from app.routers.word import router
from app.startup.offline_preload import get_readiness_snapshot, run_lifespan_startup
from app.startup.readiness_gate import SearchGateBlocked


class FrontendNoCacheMiddleware(BaseHTTPMiddleware):
    """避免瀏覽器快取 frontend HTML（內嵌就緒閘文案與邏輯）。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/frontend/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_lifespan_startup()
    yield


app = FastAPI(title="Canto-0243", lifespan=lifespan)

app.add_middleware(FrontendNoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")
app.include_router(router)
app.include_router(relation_router)
app.include_router(lexicon_router)


@app.exception_handler(SearchGateBlocked)
async def search_gate_blocked_handler(_request: Request, exc: SearchGateBlocked) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=exc.snapshot,
        headers={"Retry-After": "1"},
    )


@app.get("/")
async def home():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    base = f"http://{host}:{port}"
    return {
        "status": "running",
        "portable": bool(os.getenv("PORTABLE")),
        "port": port,
        "frontend": f"{base}/frontend/index.html",
        "api_test": f"{base}/words/search/?q=23",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def root_favicon() -> FileResponse:
    return FileResponse("frontend/favicon.ico")


@app.get("/ready")
async def preload_ready():
    return get_readiness_snapshot()


if __name__ == "__main__":
    env = os.getenv("ENV", "local").lower()
    # 預設單行程（無 StatReload）：避免 SQLite 雙行程、預載重跑、幽靈 LISTEN。
    # 需要存檔自動重載時：UVICORN_RELOAD=1 ./start.sh
    reload_opt_in = os.getenv("UVICORN_RELOAD", "").lower() in ("1", "true", "yes")
    use_reload = reload_opt_in and env != "prod" and not os.getenv("PORTABLE")
    # reload 時父行程與 worker 分離；DB bootstrap 僅在 lifespan（worker）執行，避免 SQLite 鎖導致詞庫預載失敗。
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=use_reload,
    )
