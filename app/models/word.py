from sqlalchemy import Column, Integer, String, Text, Index
from app.database import Base

# 支援 vector embeddings（semantic similarity 排序優化）
# - PostgreSQL + pgvector: 使用 Vector(384)
# - SQLite（本地開發）: 退回 String（儲存 JSON 序列化的 float list）
# 兩邊都在 import_data 時計算 embedding，並在搜尋排序中融入 semantic score
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    char = Column(String(50), index=True)
    code = Column(String(20), index=True)
    jyutping = Column(String(100))

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
    if Vector is not None:
        embedding = Column(Vector(384), nullable=True)
    else:
        embedding = Column(String(4096), nullable=True)  # JSON 序列化 float list 作為 SQLite 儲存


# 可選：額外複合索引（效能更好）
Index('idx_code_char', Word.code, Word.char)