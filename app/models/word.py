from sqlalchemy import Column, Integer, String, Text, Index, ForeignKey, Float, BigInteger, UniqueConstraint, event
from app.database import Base

# 支援 vector embeddings（semantic similarity 排序優化）
# - PostgreSQL + pgvector: 使用 Vector(384) + hnsw index (見 database.py ensure)
# - SQLite（本地開發）: 退回 String（儲存 JSON 序列化的 float list）
# 兩邊都在 import_data 時計算 embedding，並在搜尋排序中融入 semantic score
# 注意：根據 Supabase Postgres Best Practices，embedding 計算已隔離到 dev/ingest (generate_relationships.py)
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

# Module-level type selection (cleaner than conditional inside class body)
_id_type = BigInteger().with_variant(Integer, "sqlite")


class Word(Base):
    __tablename__ = "words"

    # Primary key: BigInteger + identity recommended by Supabase Postgres Best Practices
    # for better index locality and to avoid fragmentation (vs serial or random UUID).
    # For SQLite ok; for Postgres use migration to set GENERATED ALWAYS AS IDENTITY.
    id = Column(_id_type, primary_key=True, index=True)
    char = Column(String(50), index=True)
    code = Column(String(20), index=True)
    jyutping = Column(String(100))

    # Index on jyutping for jyut fragment searches (ilike %q%). For Postgres % leading wildcard,
    # consider pg_trgm extension + GIN index for better perf on broad searches (per query best practices).
    # Current path caps results (limit 500) so acceptable.

    # Explicit length column for fast indexed filtering on word length (used heavily by hybrid, wildcard, =, code searches)
    # Populated on insert and via migration for old rows. Greatly speeds up length==N queries vs func.length every time.
    length = Column(Integer, index=True, nullable=True)

    # 加上 index（你朋友建議的）
    initials = Column(String(200), index=True)
    finals = Column(String(200), index=True)
    tones = Column(String(100), index=True)

    meaning = Column(Text)

    # Vector embedding for semantic similarity sorting (同時支援 Postgres 與 SQLite)
    # 384 dim 對應 sentence-transformers paraphrase-multilingual-MiniLM-L12-v2
    # Postgres 端會在 migration 中建立 pgvector extension + index
    #
    # Refactored for cleaner module-level definition (avoids executing conditional
    # logic inside class body at import time). The actual column type for PG
    # is managed via Alembic migration + pgvector; SQLite falls back to TEXT/JSON.
    _embedding_type = Vector(384) if Vector is not None else String(4096)
    embedding = Column(_embedding_type, nullable=True)  # JSON 序列化 float list 作為 SQLite 儲存


# Additional index for jyutping searches (see comment above)
Index('idx_jyutping', Word.jyutping)

# 可選：額外複合索引（效能更好）
Index('idx_code_char', Word.code, Word.char)
Index('idx_length_code_model', Word.length, Word.code)
Index('idx_length_code_finals_model', Word.length, Word.code, Word.finals)


# ============================================================
# WordRelation：預先計算的同義/反義/語意關係（ingest 階段產生）
# ============================================================
# 應用 Supabase Postgres Best Practices (precompute for perf, avoid runtime heavy ops)
# 目標：讓 syn/ant 搜尋走純 SQL（快速、可預期），而非 runtime 依賴
# sentence-transformers + numpy matrix。
#
# relation_type 建議值：
#   'syn'               - 近義詞（優先來自 static thesaurus 如 cilin）
#   'ant'               - 反義詞（優先來自 antisem / thesaurus）
#   'semantic_related'  - 較寬鬆的語意相關（可選，由 embedding 輔助發現）
#
# source 記錄資料來源，便於之後審計或過濾：
#   'cilin', 'antisem', 'guotong', 'embedding_cosine', 'hybrid', 'manual'
#
# 這個表在 ingest 時（generate_relationships.py）由 maintainer 用 dev deps 產生。
# 一般使用者執行服務時不需要 sentence-transformers。
#
# 對應的 ensure 函式在 app/database.py（SQLite 自動建立，PG 建議用 Alembic）。
# 複合索引符合 query perf 最佳實踐（indexes on filter columns for relations）。
class WordRelation(Base):
    __tablename__ = "word_relations"
    __table_args__ = (
        UniqueConstraint("word_id", "related_id", "relation_type", name="uq_word_relation"),
    )

    # FKs to words.id (now BigInteger per best practices)
    id = Column(_id_type, primary_key=True)
    word_id = Column(_id_type, ForeignKey("words.id"), index=True, nullable=False)
    related_id = Column(_id_type, ForeignKey("words.id"), index=True, nullable=False)

    relation_type = Column(String(16), index=True, nullable=False)  # syn / ant / semantic_related
    score = Column(Float, nullable=True)                            # 可選信心分數（cosine 或人工）
    source = Column(String(32), nullable=True)                      # cilin / antisem / embedding_cosine ...

    # 常見查詢會用 (word_id, relation_type) 與 (related_id, relation_type)
    # 建議在 ensure 階段建立複合索引


# 額外複合索引（推薦用於 syn/ant 查詢）
Index("idx_word_rel_word_type", WordRelation.word_id, WordRelation.relation_type)
Index("idx_word_rel_related_type", WordRelation.related_id, WordRelation.relation_type)


@event.listens_for(WordRelation, "before_insert")
@event.listens_for(WordRelation, "before_update")
def _canonicalize_word_relation(_mapper, _connection, target: WordRelation) -> None:
    from ingest.relation_canonical import canonical_word_ids
    w, r = canonical_word_ids(int(target.word_id), int(target.related_id))
    target.word_id = w
    target.related_id = r


class SynAntEdge(Base):
    """Staging table for syn/ant ingest v2 (normalized char-level edges before merge)."""

    __tablename__ = "syn_ant_edges"

    id = Column(_id_type, primary_key=True, autoincrement=True)
    head_char = Column(String(50), index=True, nullable=False)
    tail_char = Column(String(50), index=True, nullable=False)
    relation_type = Column(String(16), index=True, nullable=False)
    source = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    source_rank = Column(Integer, nullable=True)
    evidence = Column(Text, nullable=True)
    license_tag = Column(String(32), nullable=True)
    in_db_head = Column(Integer, nullable=True)  # SQLite bool as 0/1
    in_db_tail = Column(Integer, nullable=True)


Index("idx_syn_ant_head_type", SynAntEdge.head_char, SynAntEdge.relation_type)
Index("idx_syn_ant_tail_type", SynAntEdge.tail_char, SynAntEdge.relation_type)