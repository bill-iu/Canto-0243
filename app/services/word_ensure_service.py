from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.lexicon.port import LexiconPort, default_lexicon_port
from app.domain.lexicon.word_inject import (
    ensure_word_rows_db,
    inject_lexicon_rows_db,
    sync_word_rows_to_cache,
)
from app.lexicon.static_index import LexiconEntry
from app.models.word import Word
from app.utils.word_cache import get_char_meta


def sync_word_to_cache(row) -> None:
    sync_word_rows_to_cache([row])


def inject_lexicon_entries(db: Session, text: str, entries: List[LexiconEntry]) -> List[Word]:
    """補入詞級標音列（已有同 code 列則跳過）。"""
    return inject_lexicon_rows_db(db, text, entries, after_commit=sync_word_rows_to_cache)


def ensure_word_in_db(
    db: Session,
    text: str,
    *,
    lexicon: Optional[LexiconPort] = None,
) -> List[Word]:
    return ensure_word_rows_db(
        db, text, lexicon=lexicon, after_commit=sync_word_rows_to_cache
    )


def warm_ref_char_for_lookup(last_ch: str, db: Session) -> None:
    """詞條 lookup 版面尾字韻錨前：快取無 meta 時將詞庫列同步至索引。"""
    if not last_ch or (get_char_meta(last_ch) or {}).get("finals"):
        return
    ref_row = db.query(Word).filter(Word.char == last_ch).first()
    if ref_row:
        sync_word_to_cache(ref_row)
