from __future__ import annotations

from typing import Optional

from app.models.word import Word
from app.utils.jyutping_codec import get_code_variants


def length_filter(length: int):
    return Word.length == length


def apply_code_filter(query, code: Optional[str], mode: str):
    if code:
        variants = get_code_variants(code, mode)
        query = query.filter(Word.code.in_(variants))
    return query
