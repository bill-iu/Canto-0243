from fastapi import FastAPI
import uvicorn
from app.database import Base, engine
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from app.routers.word import router

app = FastAPI(title="0243 歌詞搜尋工具")
# 建立資料表
Base.metadata.create_all(bind=engine)
app.include_router(router)

@app.get("/")
def read_root():
    return {
        "message": "歡迎使用 0243 歌詞搜尋工具！",
        "status": "正在開發中..."
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)