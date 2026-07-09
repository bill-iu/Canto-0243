"""教學探針暖機 — 對齊就緒閘解鎖（CONTEXT § 搜尋教學驗收）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.query_dispatch import search_words
from app.utils.word_cache import (
    complete_preload,
    is_word_cache_ready,
    populate_word_cache_from_rows,
)

READINESS_PROBE_QUERY = "事業"


def _load_word_cache_rows(db: Session) -> list:
    return (
        db.query(
            Word.char,
            Word.code,
            Word.jyutping,
            Word.finals,
            Word.initials,
            Word.length,
        )
        .filter(Word.length <= 10)
        .all()
    )


def warm_guide_probe_readiness(db: Session) -> None:
    """閘前：詞庫快取索引 + 事業探針（唔等 tail）。"""
    if not is_word_cache_ready():
        populate_word_cache_from_rows(_load_word_cache_rows(db))
        complete_preload()

    items = search_words(
        q=READINESS_PROBE_QUERY,
        mode="m1",
        limit=10,
        offset=0,
        db=db,
    )
    if not items:
        raise RuntimeError(
            f"guide probe readiness: {READINESS_PROBE_QUERY!r} returned 0 rows"
        )