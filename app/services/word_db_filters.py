from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, func, or_

from app.models.word import Word
from utils import get_code_variants


def length_filter(length: int):
    return or_(
        Word.length == length,
        and_(or_(Word.length.is_(None), Word.length == 0), func.length(Word.char) == length),
    )


def apply_code_filter(query, code: Optional[str], mode: str):
    if code:
        variants = get_code_variants(code, mode)
        query = query.filter(Word.code.in_(variants))
    return query
