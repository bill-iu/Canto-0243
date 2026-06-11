import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 根據 ENV 環境變數決定載入哪個 .env 檔案
ENV = os.getenv("ENV", "local").lower()

if ENV == "prod":
    env_file = ".env.prod"
else:
    env_file = ".env.local"

print(f"[ENV] 目前環境: {ENV.upper()} | 載入設定檔: {env_file}")

# 載入對應的 .env 檔案
load_dotenv(env_file)

# 讀取 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ 警告：找不到 DATABASE_URL，使用 SQLite 作為後備")
    DATABASE_URL = "sqlite:///./lyrics.db"

print(f"[DB] 使用資料庫: {DATABASE_URL.split('://')[0]}")

# 偵測資料庫類型（供跨資料庫相容層使用）
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

# 建立 engine
if IS_POSTGRES:
    # Connection pooling per Supabase Postgres Best Practices (conn-pooling rule):
    # For high concurrency or serverless (Supabase), prefer external pooler like PgBouncer
    # in transaction mode. These settings are a starting point; tune based on CPU/cores.
    # pool_size ~ (cores * 2), use pooler connection string in prod if possible.
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )
else:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False, "timeout": 30}  # 增加 timeout 減少 "database is locked" 機率（尤其在 backfill 或多程序時）
    )

# 為本地 SQLite 開發自動補上 embedding 欄位（避免 "no such column: words.embedding"）
# Postgres 正式環境應透過 Alembic migration 處理 schema 變更。
#
# 使用 Supabase Postgres Best Practices skill 建議：
# - Primary key 改用 BigInteger + identity (已在 model 更新)
# - 為 embedding 建立 vector 索引 (hnsw for cosine)
# - 確保 connection pooling 配置 (已在 engine)
# - 預先計算關係 (word_relations) 避免 runtime 計算
if not IS_POSTGRES:
    try:
        inspector = inspect(engine)
        if 'words' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('words')]
            if 'embedding' not in columns:
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

# 注意：所有 schema 確保與 backfill 邏輯已移出模組頂層（避免 uvicorn reload / multiprocessing spawn 時
# 在 child process import 階段執行重型 DB 操作，導致 KeyboardInterrupt 或 reload 失敗）。
# 請在 main.py 的 __main__ 區塊中**顯式**呼叫 ensure_length_column() 與 start_length_backfill()。
# 這樣 import database 時完全無副作用，reload 安全。

def ensure_length_column() -> None:
    """輕量 schema 確保：只負責 ALTER 與建立 index（如果需要）。"""
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if 'words' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('words')]
            column_existed = 'length' in columns
            if not column_existed:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE words ADD COLUMN length INTEGER"))
                    conn.commit()
                print("[DB] 已為本地 SQLite 資料表自動新增 'length' 欄位。")

            # 建立 index（冪等）
            # 應用 query-missing-indexes 最佳實踐：為常用 filter (length) 建立 index
            with engine.connect() as conn:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_words_length ON words(length)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_length_code ON words(length, code)"))
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
    """
    如果有需要回填的 length，啟動一個 daemon 背景執行緒去做批次更新。
    不阻塞呼叫端（適合在 __main__ 啟動後呼叫）。
    使用安全的 id subquery 寫法，避免 SQLite UPDATE ... LIMIT 語法錯誤。
    """
    if IS_POSTGRES:
        return
    try:
        inspector = inspect(engine)
        if 'words' not in inspector.get_table_names():
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

            import threading
            import time

            def _backfill_length_in_background():
                BATCH = 100  # small to avoid SQLite param limit (~999) on IN tuple
                total_updated = 0
                try:
                    with engine.connect() as bg_conn:
                        while True:
                            # 安全寫法：先用子查詢取 id（相容各種 SQLite 版本，無 raw LIMIT on UPDATE）
                            id_rows = bg_conn.execute(
                                text(
                                    "SELECT id FROM words "
                                    "WHERE (length IS NULL OR length = 0) "
                                    "ORDER BY id LIMIT :batch"
                                ),
                                {"batch": BATCH}
                            ).fetchall()
                            ids = [r[0] for r in id_rows]
                            if not ids:
                                break

                            # 快速批量更新，使用字面 IN (ids 是信任的 int)，避免 param binding 限制和 ? 問題
                            # P2 note: ids come from our own SELECT so trusted; still prefer parameterised
                            # forms in new code. Kept for SQLite batch perf + compatibility.
                            id_list = ','.join(str(i) for i in ids)
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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def contains_substring(column, substr: str):
    """可移植的子字串檢查。
    - PostgreSQL: 使用 strpos
    - SQLite: 使用 instr
    用於 shared char / substring 邏輯，取代原本的 func.instr。
    """
    from sqlalchemy import func
    if IS_POSTGRES:
        return func.strpos(column, substr) > 0
    return func.instr(column, substr) > 0


def ensure_word_relations_table() -> None:
    """
    輕量 schema 確保：建立 word_relations 表（用來存放預先計算的 syn/ant/related 關係）。
    - SQLite：自動 CREATE TABLE + 索引（ingest 時由 generate_relationships.py 產生資料）。
    - PostgreSQL：印出提示，請使用 Alembic migration 正式管理。
    這個表讓 syn/ant 搜尋可以走純 SQL，不需要在 runtime 載入 ML 模型。
    """
    if IS_POSTGRES:
        print("[DB] PostgreSQL 環境：建議使用 Alembic 建立 word_relations 表及索引。")
        print("     範例 migration 會在後續文件提供。")
        # 為 embedding 建立 vector 索引 (使用 Supabase Postgres Best Practices)
        try:
            with engine.connect() as conn:
                # hnsw index for cosine similarity (pgvector)
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_words_embedding_hnsw 
                    ON words USING hnsw (embedding vector_cosine_ops);
                """))
                conn.commit()
            print("[DB] 已確保 Postgres embedding vector 索引 (hnsw for cosine)。")
        except Exception as e:
            print(f"[DB] 建立 embedding vector index 時發生錯誤（可忽略，若 pgvector extension 未啟用或 migration 稍後處理）：{e}")
        return

    try:
        inspector = inspect(engine)
        if 'words' not in inspector.get_table_names():
            return

        if 'word_relations' not in inspector.get_table_names():
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS word_relations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word_id INTEGER NOT NULL,
                        related_id INTEGER NOT NULL,
                        relation_type VARCHAR(16) NOT NULL,
                        score FLOAT,
                        source VARCHAR(32)
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_word_rel_word_type
                    ON word_relations (word_id, relation_type)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_word_rel_related_type
                    ON word_relations (related_id, relation_type)
                """))
                conn.commit()
            print("[DB] 已為本地 SQLite 自動建立 word_relations 表與常用索引。")
        else:
            # 表已存在，確保索引存在（冪等）
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_word_rel_word_type
                    ON word_relations (word_id, relation_type)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_word_rel_related_type
                    ON word_relations (related_id, relation_type)
                """))
                conn.commit()
    except Exception as e:  # P1 fix: surface exception type
        err = str(e)
        if "database is locked" in err.lower() or "operationalerror" in err.lower():
            print("[DB] ⚠️  偵測到 database is locked，無法自動建立 word_relations。")
            print("     請關閉其他程序後重試，或手動建立表格。")
        else:
            print(f"[DB] 嘗試建立 word_relations 表時發生錯誤（可忽略，若之後執行 generate script 即可）：{type(e).__name__}: {e}")