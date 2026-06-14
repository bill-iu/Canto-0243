import os

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.relation import router as relation_router
from app.routers.word import router
from app.startup.offline_preload import get_readiness_snapshot, run_lifespan_startup, run_main_block_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_lifespan_startup()
    yield


app = FastAPI(title="Canto-0243", lifespan=lifespan)

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


@app.get("/")
async def home():
    return {
        "status": "running",
        "portable": bool(os.getenv("PORTABLE")),
        "frontend": "http://127.0.0.1:8000/frontend/index.html",
        "api_test": "http://127.0.0.1:8000/words/search/?q=23",
    }


@app.get("/ready")
async def preload_ready():
    return get_readiness_snapshot()


if __name__ == "__main__":
    env = os.getenv("ENV", "local").lower()
    run_main_block_startup(env=env)

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "local").lower() != "prod" and not os.getenv("PORTABLE"),
    )
