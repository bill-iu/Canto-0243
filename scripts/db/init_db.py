import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import Base, engine, IS_POSTGRES
from app.models.word import Word  # noqa: F401 — ensure models registered

print("正在初始化資料庫...")

env = os.getenv("ENV", "local").lower()
if (env == "prod" or IS_POSTGRES) and not os.getenv("FORCE_CREATE_ALL"):
    print("ℹ️  偵測到正式環境 (ENV=prod 或 PostgreSQL)。")
    print("   建議使用 Alembic 進行 schema 初始化/升級：alembic upgrade head")
    print("   如需使用 create_all（開發測試用），請設定 FORCE_CREATE_ALL=1 後再執行。")
    if not os.getenv("FORCE_CREATE_ALL"):
        print("已跳過 create_all。")
        print("✅ 提示完成（未執行 create_all）。")
        raise SystemExit(0)

Base.metadata.create_all(bind=engine)

print("✅ 資料庫初始化完成！")
print(f"資料庫位置: {engine.url}")
