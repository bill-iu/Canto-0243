from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.database import Base, engine
from app.routers.word import router   # ← 直接引入，不要 as

app = FastAPI(title="0243 押韻字典")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載前端
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# 註冊 Router（不要重複 prefix）
app.include_router(router)

@app.get("/")
async def home():
    return {
        "status": "running",
        "frontend": "http://127.0.0.1:8000/frontend/index.html",
        "api_test": "http://127.0.0.1:8000/words/search/?q=23"
    }

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)