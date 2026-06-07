from sqlalchemy import Column, Integer, String, Text
from app.database import Base
import json

class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True, index=True)
    char = Column(String(50), index=True)                    # 移除 UNIQUE
    code = Column(String(50), index=True)
    jyutping = Column(String(200), index=True)
    
    initials = Column(String(200))
    finals = Column(String(200))
    tones = Column(String(100))
    
    meaning = Column(Text, nullable=True)