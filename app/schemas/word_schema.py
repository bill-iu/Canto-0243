from pydantic import BaseModel
from typing import Optional

class WordBase(BaseModel):
    char: str
    code: str
    jyutping: str

class WordCreate(WordBase):
    pass

class WordRead(WordBase):
    id: int

    class Config:
        from_attributes = True