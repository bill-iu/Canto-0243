from typing import Literal

from pydantic import BaseModel


class LexiconCorrectionCreate(BaseModel):
    char: str
    code: str
    jyutping: str
    action: Literal["set_jyutping", "set_code"]
    value: str
    note: str = ""


class LexiconCorrectionQueued(BaseModel):
    message: str
    pending_count: int
    char: str
    code: str
    jyutping: str
    action: str
    value: str
    note: str = ""
