from __future__ import annotations

from app.utils.json_helpers import load_json_list
from app.utils.word_cache import get_char_metas
from app.utils.jyutping_codec import rhyme_finals_from_jyutping

from app.models.word import Word
from app.services.word_ensure_service import ensure_word_in_db, sync_word_to_cache
from app.services.word_serializer import get_rhyme_finals


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
        jp = meta.get("jyutping")
        if jp:
            finals = rhyme_finals_from_jyutping(jp)
            if finals:
                options.add(finals[0])
                continue
        finals = meta.get("finals") or []
        if finals:
            options.add(finals[0])
    if options:
        return options
    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows:
        rows = ensure_word_in_db(db, ch)
    for row in rows:
        finals = get_rhyme_finals(row)
        if finals:
            options.add(finals[0])
        sync_word_to_cache(row)
    return options
