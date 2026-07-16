import os
import threading
from pathlib import Path

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response

from app.lexicon_version import lexicon_version
from app.routers.lexicon import router as lexicon_router
from app.routers.relation import router as relation_router
from app.routers.word import router
from app.startup.offline_preload import get_readiness_snapshot, run_lifespan_startup
from app.startup.readiness_gate import SearchGateBlocked

# Product UI (portable client). Import does not require the dir; lifespan does.
APP_UI_DIR = Path(os.getenv("CANTO_APP_UI", "client/dist-portable"))


def require_app_ui_dir(ui_dir: Path | None = None) -> Path:
    """Hard-fail if portable UI dist is missing — never fall back to frontend/."""
    path = ui_dir if ui_dir is not None else Path(os.getenv("CANTO_APP_UI", "client/dist-portable"))
    if not path.is_dir() or not (path / "index.html").is_file():
        raise RuntimeError(
            f"Portable UI not found at {path.resolve()}. "
            "Run: cd client && npm run build:portable "
            "(or set CANTO_APP_UI to a directory containing index.html)."
        )
    return path


def inject_app_index_meta(html: str, *, portable: bool | None = None) -> str:
    """Inject lexicon-version and optional canto-portable meta into index HTML."""
    ver = lexicon_version()
    ver_tag = f'<meta name="canto-lexicon-version" content="{ver}">'
    if 'name="canto-lexicon-version"' not in html:
        html = html.replace("<head>", f"<head>\n  {ver_tag}", 1)
    use_portable = _is_portable() if portable is None else portable
    if use_portable:
        tag = '<meta name="canto-portable" content="1">'
        if 'name="canto-portable"' not in html:
            html = html.replace("<head>", f"<head>\n  {tag}", 1)
    return html


class UiNoCacheMiddleware(BaseHTTPMiddleware):
    """Avoid caching product/legacy UI HTML (ready-gate copy + logic)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/app") or path.startswith("/frontend/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    require_app_ui_dir()
    run_lifespan_startup()
    yield


app = FastAPI(title="Canto-0243", lifespan=lifespan)

app.add_middleware(UiNoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path("frontend")


def _is_portable() -> bool:
    return os.getenv("PORTABLE", "").lower() not in ("", "0", "false", "no")


@app.get("/app/", include_in_schema=False)
@app.get("/app/index.html", include_in_schema=False)
async def serve_app_index() -> HTMLResponse:
    """Product UI entry: inject meta so reload shows exit control / lexicon version."""
    ui_dir = require_app_ui_dir()
    html = inject_app_index_meta((ui_dir / "index.html").read_text(encoding="utf-8"))
    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-cache, must-revalidate", "Pragma": "no-cache"},
    )


# check_dir=False: import-time mount must not crash unit tests without dist;
# lifespan + serve_app_index call require_app_ui_dir() for a clear hard fail.
app.mount(
    "/app",
    StaticFiles(directory=str(APP_UI_DIR), html=True, check_dir=False),
    name="app_ui",
)


def resolve_favicon(ui_dir: Path | None = None) -> Path | None:
    """Best favicon for /favicon.ico; None when no asset is available."""
    base = ui_dir if ui_dir is not None else APP_UI_DIR
    for candidate in (
        base / "favicon.ico",
        base / "favicon.svg",
        base / "icon-32.png",
        FRONTEND_DIR / "favicon.ico",
    ):
        if candidate.is_file():
            return candidate
    return None


if FRONTEND_DIR.is_dir():

    # Transitional: serve shared SSOT under /frontend for seam live-checks.
    # Product launch opens /app/ only (local_launch HTML_SUFFIX); do not document
    # /frontend/index.html as the Portable UI.
    @app.get("/frontend/index.html", include_in_schema=False)
    async def serve_frontend_index() -> HTMLResponse:
        """Legacy shell HTML for unmigrated tests. Product entry is /app/."""
        index = FRONTEND_DIR / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="frontend index not found")
        html = index.read_text(encoding="utf-8")
        return HTMLResponse(
            inject_app_index_meta(html),
            headers={"Cache-Control": "no-cache, must-revalidate", "Pragma": "no-cache"},
        )

    app.mount(
        "/frontend",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )

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
    app_url = f"{base}/app/index.html"
    return {
        "status": "running",
        "portable": _is_portable(),
        "lexiconVersion": lexicon_version(),
        "port": port,
        "app": app_url,
        "frontend": app_url,
        "api_test": f"{base}/words/search/?q=23",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def root_favicon() -> FileResponse:
    fav = resolve_favicon()
    if fav is None:
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(fav)


@app.get("/ready")
async def preload_ready():
    snap = get_readiness_snapshot()
    snap["portable"] = _is_portable()
    snap["lexiconVersion"] = lexicon_version()
    return snap


def _client_is_localhost(request: Request) -> bool:
    if not request.client:
        return False
    host = request.client.host.strip("[]")
    return host in ("127.0.0.1", "localhost", "::1") or host.startswith("127.")


@app.post("/shutdown")
async def portable_shutdown(request: Request):
    """Portable-only graceful exit (localhost callers)."""
    if not _is_portable():
        raise HTTPException(status_code=403, detail="shutdown only available in portable mode")
    if not _client_is_localhost(request):
        raise HTTPException(status_code=403, detail="shutdown only allowed from localhost")

    def _exit_soon() -> None:
        # ponytail: portable 退出用 _exit；Windows 上 SIGTERM 對 uvicorn 不可靠
        threading.Timer(0.25, lambda: os._exit(0)).start()

    _exit_soon()
    return {"ok": True, "message": "shutting down"}


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
