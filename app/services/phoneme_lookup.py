from __future__ import annotations

from utils import get_char_metas, load_json_list

from app.models.word import Word
from app.services.word_ensure_service import ensure_word_in_db, sync_word_to_cache


def initial_options_for_char(ch: str, db) -> set[str]:
    options: set[str] = set()
    for meta in get_char_metas(ch):
        initials = meta.get("initials") or []
        if initials:
            options.add(initials[0])
    if options:
        return options
    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows:
        rows = ensure_word_in_db(db, ch)
    for row in rows:
        initials = load_json_list(getattr(row, "initials", None))
        if initials:
            options.add(initials[0])
        sync_word_to_cache(row)
    return options


def final_options_for_char(ch: str, db) -> set[str]:
    options: set[str] = set()
    for meta in get_char_metas(ch):
        finals = meta.get("finals") or []
        if finals:
            options.add(finals[0])
    if options:
        return options
    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows:
        rows = ensure_word_in_db(db, ch)
    for row in rows:
        finals = load_json_list(getattr(row, "finals", None))
        if finals:
            options.add(finals[0])
        sync_word_to_cache(row)
    return options
