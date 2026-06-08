from app.database import Base, engine
import sys

def reset_database():
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