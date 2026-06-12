#!/usr/bin/env python3
"""
Backfill Script for Word Embeddings (Semantic Similarity)

用途：
  為資料庫中「已經存在但 embedding 欄位為空」的詞語，補上 vector embedding。

本地 SQLite 主 DB 瘦身後，embedding 預設不再寫入 lyrics.db。
需明確 opt-in：
  ALLOW_MAIN_DB_EMBEDDINGS=1 python scripts/legacy/backfill_embeddings.py --write-main-db
  或僅匯出旁路備份：
  python scripts/legacy/backfill_embeddings.py --export-sidecar backup/lyrics_embeddings_new.jsonl.gz

Postgres 正式環境不受 --write-main-db 限制（仍可直接 backfill）。
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.database import SessionLocal, IS_POSTGRES
from app.models.word import Word
from utils import enable_embedding_model_for_ingest, get_text_embedding


BATCH_SIZE = 500
PRINT_EVERY = 100


def _sqlite_main_db_write_allowed(write_main_db: bool) -> bool:
    if IS_POSTGRES:
        return True
    if write_main_db:
        return True
    if os.getenv("ALLOW_MAIN_DB_EMBEDDINGS", "").strip() in ("1", "true", "yes"):
        return True
    return False


def export_embeddings_sidecar(
    db: Session,
    sidecar_path: str,
    *,
    batch_size: int = 2000,
) -> int:
    """Append/update sidecar JSONL.gz with id + embedding for rows that have embeddings."""
    from pathlib import Path

    path = Path(sidecar_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    offset = 0

    with gzip.open(path, "wt", encoding="utf-8") as out:
        while True:
            batch = (
                db.query(Word.id, Word.embedding)
                .filter(Word.embedding.isnot(None), func.length(Word.embedding) > 10)
                .order_by(Word.id)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not batch:
                break
            for wid, emb in batch:
                out.write(
                    json.dumps({"id": int(wid), "embedding": emb}, ensure_ascii=False)
                    + "\n"
                )
                count += 1
            offset += len(batch)
    return count


def backfill_embeddings(
    db: Session,
    limit: Optional[int] = None,
    *,
    write_main_db: bool = False,
    sidecar_path: Optional[str] = None,
):
    """
    找出 embedding 為空或 NULL 的詞，補上 embedding。
    SQLite 預設寫入主 DB 需 --write-main-db 或 ALLOW_MAIN_DB_EMBEDDINGS=1。
    """
    if sidecar_path:
        print(f"📦 匯出現 至旁路備份: {sidecar_path}")
        n = export_embeddings_sidecar(db, sidecar_path)
        print(f"✅ 已匯出 {n} 筆 embedding 至 sidecar。")
        return

    if not _sqlite_main_db_write_allowed(write_main_db):
        print("❌ 本地 SQLite 預設不寫入主 DB embedding（主 DB 已瘦身）。")
        print("   若要寫回 lyrics.db，請使用：")
        print("     ALLOW_MAIN_DB_EMBEDDINGS=1 python scripts/legacy/backfill_embeddings.py --write-main-db")
        print("   或只匯出旁路備份：")
        print("     python scripts/legacy/backfill_embeddings.py --export-sidecar backup/lyrics_embeddings.jsonl.gz")
        return

    print("🔍 正在查詢需要 backfill embedding 的詞語...")

    query = db.query(Word).filter(
        or_(
            Word.embedding.is_(None),
            Word.embedding == "",
            func.length(Word.embedding) < 10,
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
            text_for_embed = word.char or word.jyutping or ""
            if not text_for_embed.strip():
                skipped += 1
                continue

            try:
                emb = get_text_embedding(text_for_embed)
                if emb:
                    if IS_POSTGRES:
                        word.embedding = emb
                    else:
                        word.embedding = json.dumps(emb)
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ⚠️  處理「{word.char}」時發生錯誤: {e}")
                skipped += 1

            if processed % PRINT_EVERY == 0:
                print(
                    f"  已處理 {processed}/{total_to_process} 筆... "
                    f"(更新 {updated}, 跳過 {skipped})"
                )

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
    parser = argparse.ArgumentParser(description="Backfill word embeddings (dev/ingest)")
    parser.add_argument(
        "--write-main-db",
        action="store_true",
        help="Write embeddings into main lyrics.db (SQLite requires ALLOW_MAIN_DB_EMBEDDINGS=1)",
    )
    parser.add_argument(
        "--export-sidecar",
        metavar="PATH",
        help="Export existing embeddings to gzip JSONL sidecar instead of backfill",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max rows to backfill")
    args = parser.parse_args()

    print("🚀 啟動 Embedding Backfill Script")
    print(f"資料庫類型: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    print(f"ENV: {os.getenv('ENV', 'local')}")
    print()

    if args.export_sidecar:
        db = SessionLocal()
        try:
            export_embeddings_sidecar(db, args.export_sidecar)
        finally:
            db.close()
        return

    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        print("❌ 錯誤：沒有安裝 sentence-transformers")
        print("    pip install sentence-transformers")
        sys.exit(1)

    try:
        import warnings

        warnings.filterwarnings(
            "ignore",
            message=".*You are sending unauthenticated requests to the HF Hub.*",
        )
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    except Exception:
        pass

    enable_embedding_model_for_ingest()

    db = SessionLocal()
    try:
        backfill_embeddings(
            db,
            limit=args.limit,
            write_main_db=args.write_main_db,
            sidecar_path=args.export_sidecar,
        )
    finally:
        db.close()

    print("\n提示：")
    print("  SQLite 主 DB 預設不寫入 embedding；使用 --write-main-db + ALLOW_MAIN_DB_EMBEDDINGS=1 才會寫回。")


if __name__ == "__main__":
    main()
