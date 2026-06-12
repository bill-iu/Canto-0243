"""SQLite dev schema patches and background maintenance (explicit startup only)."""

from __future__ import annotations

import threading
import time

from sqlalchemy import inspect, text

from app.db.connection import IS_POSTGRES, engine


def ensure_embedding_column() -> None:
    """為本地 SQLite 自動補上 embedding 欄位（Postgres 走 Alembic）。"""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if "words" not in inspector.get_table_names():
            return
        columns = [col["name"] for col in inspector.get_columns("words")]
        if "embedding" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE words ADD COLUMN embedding TEXT"))
                conn.commit()
            print("[DB] 已為本地 SQLite 資料表自動新增 'embedding' 欄位（semantic search 支援）。")
    except KeyboardInterrupt:
        print("[DB] ⚠️  embedding 欄位檢查在啟動時被中斷。應用將繼續啟動。")
    except Exception as e:
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked（另一程序如 backfill 可能還在持有連線）。")
            print("     請關閉其他 python/uvicorn/backfill 程序後重新啟動本應用，即可自動補欄位。")
            print("     本次啟動將繼續（若欄位已存在則無影響）。")
        else:
            print(f"[DB] 嘗試新增 embedding 欄位時發生錯誤（可忽略，若之後執行 init_db 或重置即可）：{e}")


def ensure_length_column() -> None:
    """輕量 schema 確保：只負責 ALTER 與建立 index（如果需要）。"""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if "words" not in inspector.get_table_names():
            return
        columns = [col["name"] for col in inspector.get_columns("words")]
        column_existed = "length" in columns
        if not column_existed:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE words ADD COLUMN length INTEGER"))
                conn.commit()
            print("[DB] 已為本地 SQLite 資料表自動新增 'length' 欄位。")

        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_words_length ON words(length)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_length_code ON words(length, code)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_length_code_finals ON words(length, code, finals)"))
            conn.commit()
        if not column_existed:
            print("[DB] length 相關 index 已確保。")
    except Exception as e:
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked（另一程序如 backfill 可能還在持有連線）。")
            print("     請關閉其他 python/uvicorn/backfill 程序後重新啟動本應用，即可自動補 length 欄位與索引。")
        else:
            print(f"[DB] 嘗試處理 length 欄位時發生錯誤（可忽略，若之後執行 init_db 或重置即可）：{e}")


def start_length_backfill() -> None:
    """若有需要回填的 length，啟動 daemon 背景執行緒批次更新（不阻塞啟動）。"""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if "words" not in inspector.get_table_names():
            return
        with engine.connect() as conn:
            null_count = conn.execute(
                text("SELECT COUNT(*) FROM words WHERE length IS NULL OR length = 0")
            ).scalar() or 0

            if null_count == 0:
                return

            print(f"[DB] 偵測到 {null_count} 筆資料需要 length 回填。")
            print("[DB] 將在背景執行緒中批次回填（不阻塞啟動 / reload）。")
            print("[DB] 搜尋功能會使用防禦性 fallback（_length_filter），結果正確但暫時較慢。")

            def _backfill_length_in_background():
                batch = 100
                total_updated = 0
                try:
                    with engine.connect() as bg_conn:
                        while True:
                            id_rows = bg_conn.execute(
                                text(
                                    "SELECT id FROM words "
                                    "WHERE (length IS NULL OR length = 0) "
                                    "ORDER BY id LIMIT :batch"
                                ),
                                {"batch": batch},
                            ).fetchall()
                            ids = [r[0] for r in id_rows]
                            if not ids:
                                break

                            id_list = ",".join(str(i) for i in ids)
                            res = bg_conn.execute(
                                text(f"UPDATE words SET length = length(char) WHERE id IN ({id_list})")
                            )
                            updated = res.rowcount or 0
                            bg_conn.commit()
                            total_updated += updated
                            if total_updated % 10000 == 0:
                                print(f"[DB]   length 背景回填進度：{total_updated} / ~{null_count} 筆...")
                            time.sleep(0.005)
                    print(f"[DB] length 背景回填完成，共更新 {total_updated} 筆。")
                except Exception as bg_err:
                    print(f"[DB] length 背景回填發生錯誤（可忽略，下次起動會繼續）：{bg_err}")

            t = threading.Thread(target=_backfill_length_in_background, daemon=True)
            t.start()
    except Exception as e:
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked，無法啟動 length 背景回填。")
        else:
            print(f"[DB] 啟動 length 背景回填時發生錯誤（可忽略）：{e}")


def ensure_word_relations_canonical_unique() -> None:
    """Canonicalize (min word_id first) and enforce unique (word_id, related_id, relation_type)."""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if "word_relations" not in inspector.get_table_names():
            return
        with engine.connect() as conn:
            indexes = {
                row[0]: row[1]
                for row in conn.execute(
                    text("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='word_relations'")
                ).fetchall()
            }
            if "uq_word_relation" in indexes and "uq_word_relation_pair" not in indexes:
                return
            conn.execute(text("DELETE FROM word_relations WHERE word_id > related_id"))
            conn.execute(
                text(
                    """
                DELETE FROM word_relations
                WHERE id NOT IN (
                    SELECT MIN(id) FROM word_relations
                    GROUP BY word_id, related_id, relation_type
                )
            """
                )
            )
            conn.execute(text("DROP INDEX IF EXISTS uq_word_relation_pair"))
            conn.execute(text("DROP INDEX IF EXISTS uq_word_relation"))
            conn.execute(
                text(
                    """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_word_relation
                ON word_relations (word_id, related_id, relation_type)
            """
                )
            )
            conn.commit()
            print("[DB] word_relations 已正規化為 (min_id, max_id, relation_type) 唯一。")
    except Exception as e:
        print(f"[DB] 更新 word_relations 唯一約束時發生錯誤：{type(e).__name__}: {e}")


def ensure_word_relations_pair_unique() -> None:
    """Deprecated alias — use ensure_word_relations_canonical_unique."""
    ensure_word_relations_canonical_unique()


def ensure_word_relations_group_codes_column() -> None:
    """Add group_codes column to word_relations (Cilin hierarchy for sort). Idempotent."""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if "word_relations" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("word_relations")}
        if "group_codes" in cols:
            return
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE word_relations ADD COLUMN group_codes TEXT"))
            conn.commit()
        print("[DB] 已為 word_relations 新增 group_codes 欄位（Cilin 階層 codes）。")
    except Exception as e:
        print(f"[DB] 新增 word_relations.group_codes 欄位時發生錯誤（可忽略）：{type(e).__name__}: {e}")


def ensure_word_relations_table() -> None:
    """建立 word_relations 表與索引（SQLite 自動；Postgres 提示 Alembic + 可選 vector index）。"""
    if IS_POSTGRES:
        print("[DB] PostgreSQL 環境：建議使用 Alembic 建立 word_relations 表及索引。")
        print("     範例 migration 會在後續文件提供。")
        try:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_words_embedding_hnsw
                    ON words USING hnsw (embedding vector_cosine_ops);
                """
                    )
                )
                conn.commit()
            print("[DB] 已確保 Postgres embedding vector 索引 (hnsw for cosine)。")
        except Exception as e:
            print(
                f"[DB] 建立 embedding vector index 時發生錯誤（可忽略，若 pgvector extension 未啟用或 migration 稍後處理）：{e}"
            )
        return

    try:
        inspector = inspect(engine)
        if "words" not in inspector.get_table_names():
            return

        if "word_relations" not in inspector.get_table_names():
            with engine.connect() as conn:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS word_relations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word_id INTEGER NOT NULL,
                        related_id INTEGER NOT NULL,
                        relation_type VARCHAR(16) NOT NULL,
                        score FLOAT,
                        source VARCHAR(32),
                        group_codes TEXT
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_word_rel_word_type
                    ON word_relations (word_id, relation_type)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_word_rel_related_type
                    ON word_relations (related_id, relation_type)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_word_relation
                    ON word_relations (word_id, related_id, relation_type)
                """
                    )
                )
                conn.commit()
            print("[DB] 已為本地 SQLite 自動建立 word_relations 表與常用索引。")
        else:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_word_rel_word_type
                    ON word_relations (word_id, relation_type)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_word_rel_related_type
                    ON word_relations (related_id, relation_type)
                """
                    )
                )
                conn.commit()
            ensure_word_relations_canonical_unique()
            ensure_word_relations_group_codes_column()
    except Exception as e:
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked，無法自動建立 word_relations。")
            print("     請關閉其他程序後重試，或手動建立表格。")
        else:
            print(
                f"[DB] 嘗試建立 word_relations 表時發生錯誤（可忽略，若之後執行 generate script 即可）：{type(e).__name__}: {e}"
            )


def ensure_syn_ant_edges_table() -> None:
    """Create syn_ant_edges staging table for ingest v2 (SQLite auto-create)."""
    if IS_POSTGRES:
        print("[DB] PostgreSQL 環境：syn_ant_edges 請透過 Alembic migration 管理。")
        return

    try:
        inspector = inspect(engine)
        if "words" not in inspector.get_table_names():
            return
        if "syn_ant_edges" not in inspector.get_table_names():
            with engine.connect() as conn:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS syn_ant_edges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        head_char VARCHAR(50) NOT NULL,
                        tail_char VARCHAR(50) NOT NULL,
                        relation_type VARCHAR(16) NOT NULL,
                        source VARCHAR(64),
                        confidence FLOAT,
                        source_rank INTEGER,
                        evidence TEXT,
                        license_tag VARCHAR(32),
                        in_db_head INTEGER,
                        in_db_tail INTEGER
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_syn_ant_head_type
                    ON syn_ant_edges (head_char, relation_type)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_syn_ant_tail_type
                    ON syn_ant_edges (tail_char, relation_type)
                """
                    )
                )
                conn.commit()
            print("[DB] 已為本地 SQLite 自動建立 syn_ant_edges staging 表。")
    except Exception as e:
        print(f"[DB] 建立 syn_ant_edges 表時發生錯誤：{type(e).__name__}: {e}")


def bootstrap_local_db() -> None:
    """一次執行本地 SQLite dev bootstrap（schema 補丁 + length 背景回填）。"""
    ensure_embedding_column()
    ensure_length_column()
    ensure_word_relations_table()
    ensure_word_relations_canonical_unique()
    ensure_syn_ant_edges_table()
    start_length_backfill()
