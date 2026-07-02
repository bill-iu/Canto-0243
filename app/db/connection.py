"""SQLAlchemy engine, session factory, and declarative Base."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

ENV = os.getenv("ENV", "local").lower()
env_file = ".env.prod" if ENV == "prod" else ".env.local"

print(f"[ENV] 目前環境: {ENV.upper()} | 載入設定檔: {env_file}")

load_dotenv(env_file)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_sqlite_database_url(url: str) -> str:
    """將 sqlite:///./lyrics.db 解析為專案根目錄下的絕對路徑（避免 macOS Finder 啟動時 cwd 錯誤）。"""
    if not url or not url.startswith("sqlite"):
        return url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    raw = url[len(prefix) :]
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return url
    rel = raw[2:] if raw.startswith("./") else raw
    abs_path = (PROJECT_ROOT / rel).resolve()
    return f"{prefix}{abs_path.as_posix()}"


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ 警告：找不到 DATABASE_URL，使用 SQLite 作為後備")
    DATABASE_URL = "sqlite:///./lyrics.db"

DATABASE_URL = resolve_sqlite_database_url(DATABASE_URL)

print(f"[DB] 使用資料庫: {DATABASE_URL.split('://')[0]}")

if DATABASE_URL.startswith("postgresql"):
    raise SystemExit(
        "❌ 本專案已改為 SQLite-only；不支援 PostgreSQL。\n"
        "請移除/改回 DATABASE_URL（例如 sqlite:///./lyrics.db）。"
    )

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
