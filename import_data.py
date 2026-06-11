import json
import re
import sys
from pathlib import Path
from typing import Set, Tuple

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.word import Word
from utils import split_jyutping
# get_text_embedding 已移出（僅 ingest/dev 腳本使用）


def import_json_file(json_path: Path, db: Session, existing: Set[Tuple[str, str]], batch_size: int = 5000):
    """單一檔案匯入"""
    print(f"正在處理: {json_path.name} ...")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    skipped = 0

    for item in data:
        char = str(item.get("char") or "").strip()
        jyutping = str(item.get("jyutping") or "").strip()
        code = str(item.get("code") or "").strip()

        if not char or not re.search(r"[\u4e00-\u9fff]", char):
            skipped += 1
            continue

        key = (char, code)
        if key in existing:
            skipped += 1
            continue

        initials, finals, tones = split_jyutping(jyutping)

        db.add(
            Word(
                char=char,
                code=code,
                jyutping=jyutping,
                initials=initials,
                finals=finals,
                tones=tones,
                length=len(char),
                # embedding 計算已移至 ingest 專用腳本（generate_relationships.py / dev deps）。
                # 這裡不再強制計算，讓一般使用者不需要 ML 套件。
            )
        )
        existing.add(key)
        count += 1

        if count % batch_size == 0:
            db.commit()
            print(f"  已匯入 {count} 筆...")

    db.commit()
    print(f"✅ 完成 {json_path.name}！新增 {count} 筆，重複跳過 {skipped} 筆。")
    return count, skipped


def import_all_in_folder(folder_path: str = "data/raw/clean"):
    """一次匯入整個資料夾的所有 JSON"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ 資料夾不存在: {folder}")
        return

    json_files = sorted(folder.glob("*.json"))
    if not json_files:
        print("❌ 資料夾內沒有找到任何 .json 檔案")
        return

    print(f"找到 {len(json_files)} 個 JSON 檔案，即將開始匯入...\n")

    with SessionLocal() as db:
        total_count = 0
        total_skipped = 0

        existing = {(row[0], row[1]) for row in db.query(Word.char, Word.code).all()}

        for json_file in json_files:
            count, skipped = import_json_file(json_file, db, existing)
            total_count += count
            total_skipped += skipped

        db.commit()

    print("\n" + "=" * 60)
    print("🎉 全部匯入完成！")
    print(f"總新增: {total_count} 筆")
    print(f"總跳過: {total_skipped} 筆")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with SessionLocal() as db:
            import_json_file(Path(sys.argv[1]), db, set())
    else:
        import_all_in_folder("data/raw/clean")