from sqlalchemy import BigInteger, Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event
from app.database import Base

# Module-level type selection (cleaner than conditional inside class body)
_id_type = BigInteger().with_variant(Integer, "sqlite")


class Word(Base):
    __tablename__ = "words"

    id = Column(_id_type, primary_key=True)  # INTEGER PRIMARY KEY = rowid; no extra index needed (ADR-0027)
    char = Column(String(50), index=True)
    code = Column(String(20), index=True)
    jyutping = Column(String(100))  # jyutping index removed — only used in ORDER BY, never in WHERE (ADR-0027)

    # Explicit length column for fast indexed filtering on word length
    length = Column(Integer, index=True, nullable=True)

    initials = Column(String(200), index=True)
    finals = Column(String(200), index=True)
    # tones removed — derivable from jyutping via split_jyutping(), zero runtime queries (ADR-0027)

    # Bitmask encoding ingest provenance: hsk30=1 kaifang=2 rime=4 rime_phrase=8 rime_words=16 words_hk=32
    # Replaces word_sources table (ADR-0027). Query: WHERE source_flags & 8 > 0 (rime_phrase)
    source_flags = Column(Integer, nullable=True, default=0)

    # meaning and embedding removed — always NULL, never populated (ADR-0027)


# Composite index: covers length-only, length+code, and length+code+finals queries.
# idx_length_code dropped — its prefix is fully covered by this index (ADR-0027).
Index('idx_length_code_finals_model', Word.length, Word.code, Word.finals)


# ============================================================
# WordRelation：預先計算的同義/反義/語意關係（ingest 階段產生）
# ============================================================
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
# 對應的 ensure 函式在 app/database.py（SQLite-only：啟動時 schema ensure）。
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
    # Cilin hierarchy codes (JSON array): ["A", "Aa", "Aa01", "Aa01A", "Aa01A01="] for later sort/rank
    group_codes = Column(Text, nullable=True)

    # 常見查詢會用 (word_id, relation_type) 與 (related_id, relation_type)
    # 建議在 ensure 階段建立複合索引


# 額外複合索引（推薦用於 syn/ant 查詢）
Index("idx_word_rel_word_type", WordRelation.word_id, WordRelation.relation_type)
Index("idx_word_rel_related_type", WordRelation.related_id, WordRelation.relation_type)


@event.listens_for(WordRelation, "before_insert")
@event.listens_for(WordRelation, "before_update")
def _canonicalize_word_relation(_mapper, _connection, target: WordRelation) -> None:
    from app.domain.relations.canonical import canonical_word_ids
    w, r = canonical_word_ids(int(target.word_id), int(target.related_id))
    target.word_id = w
    target.related_id = r
