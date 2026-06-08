from app.database import Base, engine
from app.models.word import Word   # 確保所有 model 都有 import

print("正在初始化資料庫...")

# 建立所有資料表
Base.metadata.create_all(bind=engine)

print("✅ 資料庫初始化完成！")
print(f"資料庫位置: {engine.url}")