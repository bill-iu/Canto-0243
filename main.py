import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers.word import router

app = FastAPI(title="0243 押韻字典")

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
    Base.metadata.create_all(bind=engine)
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "local").lower() != "prod",
    )