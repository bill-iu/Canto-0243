"""SQLite dev schema patches and background maintenance (explicit startup only)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.connection import engine
from app.domain.lexicon.length_invariant import repair_legacy_lexicon_lengths


def ensure_embedding_column() -> None:
    """為本地 SQLite 自動補上 embedding 欄位。"""
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

        # ponytail: I2 — composite idx_length_code_finals comes from SQLAlchemy model only
        if not column_existed:
            print("[DB] length 欄位已確保（索引由 build-db finalize 管理）。")
    except Exception as e:
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked（另一程序如 backfill 可能還在持有連線）。")
            print("     請關閉其他 python/uvicorn/backfill 程序後重新啟動本應用，即可自動補 length 欄位與索引。")
        else:
            print(f"[DB] 嘗試處理 length 欄位時發生錯誤（可忽略，若之後執行 init_db 或重置即可）：{e}")


def ensure_word_relations_canonical_unique() -> None:
    """Canonicalize (min word_id first) and enforce unique (word_id, related_id, relation_type)."""
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
            # ADR-0038 U1: prefer table CONSTRAINT autoindex; avoid second UNIQUE index
            table_sql = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='word_relations'")
            ).fetchone()
            has_table_unique = bool(
                table_sql
                and table_sql[0]
                and "UNIQUE" in str(table_sql[0]).upper()
                and "WORD_ID" in str(table_sql[0]).upper()
            )
            if has_table_unique and "uq_word_relation" in indexes:
                conn.execute(text("DROP INDEX IF EXISTS uq_word_relation"))
                conn.commit()
                print("[DB] dropped duplicate uq_word_relation (table UNIQUE already present).")
                return
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
            if not has_table_unique:
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
    """建立 word_relations 表與索引（SQLite 自動）。"""

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


def ensure_phoneme_compact_contract() -> None:
    """C1: local SQLite must use compact phoneme fields (auto-migrate when possible)."""
    from app.db.connection import PROJECT_ROOT
    from ingest.lexicon_meta import ensure_phoneme_storage_contract

    db_path = PROJECT_ROOT / "lyrics.db"
    if not db_path.is_file():
        return
    try:
        status = ensure_phoneme_storage_contract(db_path, allow_migrate=True)
        if status == "migrated":
            print(f"[DB] 已自動遷移音素欄位緊湊化: {db_path}")
    except Exception as e:
        print(f"[DB] 音素欄位契約: {e}")
        raise


def repair_local_length_invariant() -> int:
    """Repair legacy local databases synchronously before readiness."""
    db_path = engine.url.database
    if not db_path or db_path == ":memory:":
        raise RuntimeError("local lexicon length repair requires a file-backed SQLite database")
    repaired = repair_legacy_lexicon_lengths(db_path)
    if repaired:
        print(f"[DB] repaired words.length for {repaired} legacy rows")
    return repaired


def assert_runtime_length_invariant() -> None:
    """Strict open gate for immutable production lexicons."""
    db_path = engine.url.database
    if not db_path or db_path == ":memory:":
        raise RuntimeError("lexicon length validation requires a file-backed SQLite database")
    from app.domain.lexicon.length_invariant import assert_lexicon_length_invariant

    assert_lexicon_length_invariant(db_path)


def bootstrap_local_db() -> None:
    """一次執行本地 SQLite dev bootstrap；修復完成後才通過就緒閘。"""
    ensure_embedding_column()
    ensure_length_column()
    ensure_word_relations_table()
    ensure_word_relations_canonical_unique()
    ensure_phoneme_compact_contract()
    repair_local_length_invariant()
