from typing import Literal

from pydantic import BaseModel, Field


class ManualRelationCreate(BaseModel):
    seed_char: str = Field(..., min_length=1, description="種子字面")
    opposite_char: str = Field(..., min_length=1, description="對端字面")
    relation_type: Literal["syn", "ant"] = Field(..., description="近義或反義")


class ManualRelationResult(BaseModel):
    direct: int
    expand: int
    skipped: int
    message: str
