"""教學探針暖機 — 對齊就緒閘解鎖（CONTEXT § 搜尋教學驗收）。"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.lexicon.static_index import DEFAULT_FIXTURE_JSON
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


def _fixture_chars(path: Path = DEFAULT_FIXTURE_JSON) -> list[str]:
    """教學／指南依賴嘅詞級 fixture 字面（例：窮困潦倒）。"""
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        char = str(item.get("char") or "").strip()
        if not char or char in seen:
            continue
        seen.add(char)
        out.append(char)
    return out


def ensure_guide_fixture_words(db: Session) -> int:
    """將 word_lexicon fixture 注入 words（缺則補），並 sync 詞庫快取。"""
    from app.domain.lexicon.word_inject import SyncingWordRowInject

    inject = SyncingWordRowInject()
    n = 0
    for char in _fixture_chars():
        before = db.query(Word.id).filter(Word.char == char).count()
        rows = inject.ensure_word_rows(db, char)
        if rows and before == 0:
            n += len(rows)
    return n


def warm_guide_probe_readiness(db: Session) -> None:
    """閘前：指南 fixture → 詞庫快取索引 + 事業探針（唔等 tail）。"""
    ensure_guide_fixture_words(db)
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
