from typing import Optional

from pydantic import BaseModel


class WordBase(BaseModel):
    char: str
    code: str
    jyutping: str


class WordCreate(WordBase):
    pass


class WordRead(WordBase):
    id: Optional[int] = None
    display_text: Optional[str] = None
    query_text: Optional[str] = None
    result_type: Optional[str] = None

    class Config:
        from_attributes = True