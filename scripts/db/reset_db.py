import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import Base, engine, IS_POSTGRES


def reset_database():
    env = os.getenv("ENV", "local").lower()
    is_prod = env == "prod" or IS_POSTGRES
    if is_prod:
        print("❌ 拒絕執行：偵測到正式環境 (ENV=prod 或 PostgreSQL)。")
        print("   正式環境請使用 Alembic 管理 schema（alembic upgrade / downgrade），避免資料遺失。")
        print("   如需強制，請設定 ALLOW_RESET_PROD=1 並重新確認。")
        if os.getenv("ALLOW_RESET_PROD") != "1":
            return

    print("⚠️  警告：即將刪除資料庫中所有資料表並重新建立！")
    confirm = input("確定要繼續嗎？(yes/no): ").strip().lower()

    if confirm != "yes":
        print("已取消操作。")
        return

    print("正在刪除所有資料表...")
    Base.metadata.drop_all(bind=engine)

    print("正在重新建立所有資料表...")
    Base.metadata.create_all(bind=engine)

    print("✅ 資料庫重置完成！所有資料表已重新建立。")


if __name__ == "__main__":
    reset_database()
