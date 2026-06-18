"""詞條庫注入 — 純 DB；cache sync 由 SyncingWordRowInject / services adapter 負責。"""

from __future__ import annotations

import re
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from app.domain.lexicon.admission import resolve_admission
from app.domain.lexicon.port import LexiconPort, default_lexicon_port
from app.lexicon.static_index import LexiconEntry
from app.models.word import Word
from app.utils.jyutping_codec import split_jyutping

RowsCallback = Callable[[List], None]


def sync_word_rows_to_cache(rows: List) -> None:
    from app.utils.word_cache import update_word_in_cache

    for row in rows:
        try:
            update_word_in_cache(
                row.char,
                getattr(row, "code", "") or "",
                getattr(row, "jyutping", "") or "",
                getattr(row, "finals", None),
                getattr(row, "initials", None),
                getattr(row, "length", None),
            )
        except Exception:
            pass


def _word_from_entry(text: str, jyut_str: str, code_val: str) -> Word:
    try:
        initials, finals, tones = split_jyutping(jyut_str)
    except Exception:
        initials = finals = tones = "[]"
    return Word(
        char=text,
        code=code_val,
        jyutping=jyut_str,
        initials=initials,
        finals=finals,
        tones=tones,
        length=len(text),
        meaning=None,
    )


def inject_lexicon_rows_db(
    db: Session,
    text: str,
    entries: List[LexiconEntry],
    *,
    after_commit: RowsCallback | None = None,
) -> List[Word]:
    added_any = False
    for ent in entries:
        if not ent.jyutping or not ent.code:
            continue
        exists = (
            db.query(Word)
            .filter(Word.char == text, Word.code == ent.code)
            .first()
        )
        if exists:
            continue
        db.add(_word_from_entry(text, ent.jyutping, ent.code))
        added_any = True
    if not added_any:
        return db.query(Word).filter(Word.char == text).all()
    try:
        db.commit()
        rows = db.query(Word).filter(Word.char == text).all()
        if after_commit:
            after_commit(rows)
        print(f"[ensure] injected from lexicon: '{text}' ({len(rows)} row(s))")
        return rows
    except Exception as e:
        db.rollback()
        print(f"[ensure] lexicon DB insert failed for {text}: {type(e).__name__}: {e}")
        return []


def ensure_word_rows_db(
    db: Session,
    text: str,
    *,
    lexicon: Optional[LexiconPort] = None,
    after_commit: RowsCallback | None = None,
) -> List[Word]:
    if not text or not text.strip():
        return []
    text = text.strip()
    existing = db.query(Word).filter(Word.char == text).all()
    if existing:
        return existing
    if not re.search(r"[\u4e00-\u9fff]", text):
        return []

    port = lexicon or default_lexicon_port()
    admission = resolve_admission(text, lexicon=port)
    if not admission.can_inject:
        return []
    return inject_lexicon_rows_db(db, text, admission.entries, after_commit=after_commit)


class DbWordRowInject:
    def ensure_word_rows(self, db: Session, text: str) -> List[Word]:
        return ensure_word_rows_db(db, text)

    def inject_lexicon_rows(
        self,
        db: Session,
        text: str,
        entries: List[LexiconEntry],
    ) -> List[Word]:
        return inject_lexicon_rows_db(db, text, entries)


class SyncingWordRowInject:
    """ponytail: default port wrapper; upgrade path = inject after_commit at call site only."""

    def __init__(self, inner: DbWordRowInject | None = None) -> None:
        self._inner = inner or DbWordRowInject()

    def ensure_word_rows(self, db: Session, text: str) -> List[Word]:
        return ensure_word_rows_db(db, text, after_commit=sync_word_rows_to_cache)

    def inject_lexicon_rows(
        self,
        db: Session,
        text: str,
        entries: List[LexiconEntry],
    ) -> List[Word]:
        return inject_lexicon_rows_db(
            db, text, entries, after_commit=sync_word_rows_to_cache
        )


__all__ = [
    "DbWordRowInject",
    "SyncingWordRowInject",
    "ensure_word_rows_db",
    "inject_lexicon_rows_db",
    "sync_word_rows_to_cache",
]
