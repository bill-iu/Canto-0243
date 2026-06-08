import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 根據 ENV 環境變數決定載入哪個 .env 檔案
ENV = os.getenv("ENV", "local").lower()

if ENV == "prod":
    env_file = ".env.prod"
else:
    env_file = ".env.local"

print(f"[ENV] 目前環境: {ENV.upper()} | 載入設定檔: {env_file}")

# 載入對應的 .env 檔案
load_dotenv(env_file)

# 讀取 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ 警告：找不到 DATABASE_URL，使用 SQLite 作為後備")
    DATABASE_URL = "sqlite:///./lyrics.db"

print(f"[DB] 使用資料庫: {DATABASE_URL.split('://')[0]}")

# 建立 engine
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()