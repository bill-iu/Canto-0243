"""SQLAlchemy engine, session factory, and declarative Base."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.payload_root import get_payload_root

ENV = os.getenv("ENV", "local").lower()
# Load env from payload root first (Desktop sidecar), then cwd.
# Entry (desktop_entry) must bind CANTO_PAYLOAD_ROOT before importing this module.
_PAYLOAD = get_payload_root()
_env_name = ".env.prod" if ENV == "prod" else ".env.local"
for _candidate in (_PAYLOAD / _env_name, Path.cwd() / _env_name, Path(_env_name)):
    if _candidate.is_file():
        load_dotenv(_candidate)
        env_file = str(_candidate)
        break
else:
    load_dotenv(_env_name)
    env_file = _env_name

print(f"[ENV] 目前環境: {ENV.upper()} | 載入設定檔: {env_file}")


def resolve_sqlite_database_url(url: str) -> str:
    """Resolve sqlite:///./lyrics.db against payload root (Desktop sidecar / repo)."""
    if not url or not url.startswith("sqlite"):
        return url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    raw = url[len(prefix) :]
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return url
    rel = raw[2:] if raw.startswith("./") else raw
    abs_path = (get_payload_root() / rel).resolve()
    return f"{prefix}{abs_path.as_posix()}"


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ 警告：找不到 DATABASE_URL，使用 SQLite 作為後備")
    DATABASE_URL = "sqlite:///./lyrics.db"

DATABASE_URL = resolve_sqlite_database_url(DATABASE_URL)

_db_kind = DATABASE_URL.split("://")[0]
_db_hint = ""
if DATABASE_URL.startswith("sqlite:///"):
    _db_hint = f" | {DATABASE_URL[len('sqlite:///'):]}"
print(f"[DB] 使用資料庫: {_db_kind} | payload={get_payload_root()}{_db_hint}")

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


def __getattr__(name: str) -> Any:
    # Lazy alias so importers always see current payload root after bind.
    if name == "PROJECT_ROOT":
        return get_payload_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
