from __future__ import annotations

from app.utils.json_helpers import load_json_list
from app.utils.jyutping_codec import rhyme_finals_from_jyutping, split_jyutping

from app.domain.lexicon.admission import resolve_admission
from app.models.word import Word
from app.services.word_ensure_service import ensure_word_in_db, sync_word_to_cache
from app.services.word_serializer import get_rhyme_finals


def _initials_from_entries(entries) -> set[str]:
    options: set[str] = set()
    for ent in entries:
        if not ent.jyutping:
            continue
        initials, _, _ = split_jyutping(ent.jyutping)
        parsed = load_json_list(initials)
        if parsed:
            options.add(parsed[0])
    return options


def _finals_from_entries(entries) -> set[str]:
    options: set[str] = set()
    for ent in entries:
        if not ent.jyutping:
            continue
        finals = rhyme_finals_from_jyutping(ent.jyutping)
        if finals:
            options.add(finals[0])
    return options


def initial_options_for_char(ch: str, db) -> set[str]:
    admission = resolve_admission(ch)
    options = _initials_from_entries(admission.entries)
    if options:
        return options

    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows and admission.can_inject:
        rows = ensure_word_in_db(db, ch)
    for row in rows:
        initials = load_json_list(getattr(row, "initials", None))
        if initials:
            options.add(initials[0])
        sync_word_to_cache(row)
    return options


def final_options_for_char(ch: str, db) -> set[str]:
    admission = resolve_admission(ch)
    options = _finals_from_entries(admission.entries)
    if options:
        return options

    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows and admission.can_inject:
        rows = ensure_word_in_db(db, ch)
    for row in rows:
        finals = get_rhyme_finals(row)
        if finals:
            options.add(finals[0])
        sync_word_to_cache(row)
    return options
