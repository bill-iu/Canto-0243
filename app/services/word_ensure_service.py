from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.lexicon.admission import resolve_admission
from app.lexicon.static_index import LexiconEntry
from app.models.word import Word
from app.services.lexicon_port import LexiconPort, default_lexicon_port
from app.utils.jyutping_codec import split_jyutping
from app.utils.word_cache import update_word_in_cache


def sync_word_to_cache(row) -> None:
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


def _inject_lexicon_entries(db: Session, text: str, entries: List[LexiconEntry]) -> List[Word]:
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
        db_word = _word_from_entry(text, ent.jyutping, ent.code)
        db.add(db_word)
        added_any = True
    if not added_any:
        return db.query(Word).filter(Word.char == text).all()
    try:
        db.commit()
        rows = db.query(Word).filter(Word.char == text).all()
        for row in rows:
            sync_word_to_cache(row)
        print(f"[ensure] injected from lexicon: '{text}' ({len(rows)} row(s))")
        return rows
    except Exception as e:
        db.rollback()
        print(f"[ensure] lexicon DB insert failed for {text}: {type(e).__name__}: {e}")
        return []


def ensure_word_in_db(
    db: Session,
    text: str,
    *,
    lexicon: Optional[LexiconPort] = None,
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
    return _inject_lexicon_entries(db, text, admission.entries)
