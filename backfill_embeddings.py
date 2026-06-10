#!/usr/bin/env python3
"""
Backfill Script for Word Embeddings (Semantic Similarity)

用途：
  為資料庫中「已經存在但 embedding 欄位為空」的詞語，補上 vector embedding。

  這是因為：
  - 新增 embedding 欄位後，新匯入的資料（透過 import_data.py）會自動計算 embedding。
  - 但舊資料（lyrics.db 或 Postgres 裡的歷史資料）embedding 欄位是 NULL，
    導致 semantic similarity 排序無法對這些舊資料生效（score 會是 0）。

使用方式：
  1. 先安裝依賴（如果還沒裝）：
     pip install sentence-transformers

  2. 確保你的環境變數正確（本地 SQLite 通常不用動）：
     ENV=local python backfill_embeddings.py

  3. 正式環境（Postgres）：
     ENV=prod python backfill_embeddings.py

注意事項：
  - 這個 script 會呼叫 sentence-transformers 模型，第一次執行會下載模型（約 400MB+），
    並且計算 embedding 會比較慢（尤其是 CPU）。
  - 建議在資料量大時分批執行，或在有 GPU 的機器上跑。
  - 執行完後 semantic search 才會對舊資料也生效。
  - 如果沒有安裝 sentence-transformers，script 會直接結束並提示。
"""

import os
import sys
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

# 讓我們能 import 專案內的東西
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, IS_POSTGRES
from app.models.word import Word
from utils import get_text_embedding


BATCH_SIZE = 500          # 每處理多少筆就 commit 一次，避免記憶體爆炸
PRINT_EVERY = 100         # 每處理多少筆印一次進度


def backfill_embeddings(db: Session, limit: Optional[int] = None):
    """
    找出 embedding 為空或 NULL 的詞，補上 embedding。
    """
    print("🔍 正在查詢需要 backfill embedding 的詞語...")

    query = db.query(Word).filter(
        or_(
            Word.embedding.is_(None),
            Word.embedding == "",
            func.length(Word.embedding) < 10,   # 太短的也視為沒資料
        )
    )

    if limit:
        query = query.limit(limit)

    total_to_process = query.count()
    print(f"找到 {total_to_process} 筆需要處理的資料。")

    if total_to_process == 0:
        print("✅ 沒有需要 backfill 的資料！")
        return

    processed = 0
    updated = 0
    skipped = 0

    # 用 offset + limit 方式批次處理，比較穩（尤其是 SQLite）
    offset = 0

    while True:
        batch = (
            db.query(Word)
            .filter(
                or_(
                    Word.embedding.is_(None),
                    Word.embedding == "",
                    func.length(Word.embedding) < 10,
                )
            )
            .order_by(Word.id)
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )

        if not batch:
            break

        for word in batch:
            processed += 1

            # 優先用 char，其次用 jyutping
            text_for_embed = word.char or word.jyutping or ""
            if not text_for_embed.strip():
                skipped += 1
                continue

            try:
                emb = get_text_embedding(text_for_embed)
                if emb:
                    if IS_POSTGRES:
                        # pgvector accepts list directly
                        word.embedding = emb
                    else:
                        # SQLite String column: store as JSON string
                        import json
                        word.embedding = json.dumps(emb)
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ⚠️  處理「{word.char}」時發生錯誤: {e}")
                skipped += 1

            if processed % PRINT_EVERY == 0:
                print(f"  已處理 {processed}/{total_to_process} 筆... (更新 {updated}, 跳過 {skipped})")

        # 批次 commit
        db.commit()
        offset += len(batch)

        if limit and processed >= limit:
            break

    print("\n" + "=" * 60)
    print("🎉 Backfill 完成！")
    print(f"總共掃描: {processed} 筆")
    print(f"成功更新: {updated} 筆")
    print(f"跳過/失敗: {skipped} 筆")
    print("=" * 60)


def main():
    print("🚀 啟動 Embedding Backfill Script")
    print(f"資料庫類型: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    print(f"ENV: {os.getenv('ENV', 'local')}")
    print()

    # 檢查 sentence-transformers 是否可用
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        print("❌ 錯誤：沒有安裝 sentence-transformers")
        print("請先執行：")
        print("    pip install sentence-transformers")
        print()
        print("安裝完成後再重新執行本 script。")
        sys.exit(1)

    # 壓制長時間 backfill 時常見的 HF Hub unauthenticated warning（無害，純粹噪音）
    # 避免 PowerShell 把 stderr 當成錯誤導致整體 exit code 看起來是 1
    try:
        import warnings
        warnings.filterwarnings(
            "ignore",
            message=".*You are sending unauthenticated requests to the HF Hub.*"
        )
        import os
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    except Exception:
        pass

    db = SessionLocal()
    try:
        # 你可以傳 limit=100 來先小量測試
        backfill_embeddings(db, limit=None)
    finally:
        db.close()

    print("\n提示：")
    print("  - 如果想只處理前 200 筆測試，可以改成：")
    print("      backfill_embeddings(db, limit=200)")
    print("  - 正式環境建議在背景或有 GPU 的機器上執行。")


if __name__ == "__main__":
    main()
