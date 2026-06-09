from sqlalchemy import Column, Integer, String, Text, Index
from app.database import Base


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    char = Column(String(50), index=True)
    code = Column(String(20), index=True)
    jyutping = Column(String(100))

    # 加上 index（你朋友建議的）
    initials = Column(String(200), index=True)
    finals = Column(String(200), index=True)
    tones = Column(String(100), index=True)

    meaning = Column(Text)


# 可選：額外複合索引（效能更好）
Index('idx_code_char', Word.code, Word.char)