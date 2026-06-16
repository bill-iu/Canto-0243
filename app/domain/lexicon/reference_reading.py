"""參考字讀音解析 — CONTEXT § 參考字讀音解析 / 收錄決策。"""

from __future__ import annotations

from typing import Any, Literal, Optional, Set

from app.domain.lexicon.admission import resolve_admission
from app.models.word import Word
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.lexicon.static_index import LexiconEntry
from app.services.word_ensure_service import ensure_word_in_db
from app.services.word_serializer import get_rhyme_finals, get_word_jyutping, get_word_text
from app.utils.json_helpers import load_json_list
from app.utils.jyutping_codec import rhyme_finals_from_jyutping, split_jyutping

PhonemeDimension = Literal["initial", "final"]


def _initials_from_entries(entries: list[LexiconEntry]) -> set[str]:
    options: set[str] = set()
    for ent in entries:
        if not ent.jyutping:
            continue
        initials, _, _ = split_jyutping(ent.jyutping)
        parsed = load_json_list(initials)
        if parsed:
            options.add(parsed[0])
    return options


def _finals_from_entries(entries: list[LexiconEntry]) -> set[str]:
    options: set[str] = set()
    for ent in entries:
        if not ent.jyutping:
            continue
        finals = rhyme_finals_from_jyutping(ent.jyutping)
        if finals:
            options.add(finals[0])
    return options


def _is_aa_variant_jyutping(jyutping: str) -> bool:
    return "aa" in (jyutping or "").lower()


def _authoritative_row_sort_key(row: Any) -> tuple:
    char = get_word_text(row)
    jyut = get_word_jyutping(row)
    return (
        pron_rank_sort_value_for_word(char, jyut),
        -get_essay_frequency(char),
        1 if _is_aa_variant_jyutping(jyut) else 0,
        jyut or "",
    )


def select_authoritative_pronunciation_row(rows: list) -> Optional[Any]:
    """多讀音時選單列：pron_rank → Essay 詞頻 → 略過 aa 變體 → 粵拼序。"""
    if not rows:
        return None
    best = min(_authoritative_row_sort_key(row) for row in rows)
    for row in rows:
        if _authoritative_row_sort_key(row) == best:
            return row
    return rows[0]


def _db_rows_for_literal(literal: str, db, *, allow_inject: bool) -> list:
    rows = db.query(Word).filter(Word.char == literal).all()
    if rows or not allow_inject:
        return rows
    admission = resolve_admission(literal)
    if admission.can_inject:
        return ensure_word_in_db(db, literal)
    return []


def anchor_phoneme_options(
    char: str,
    dimension: PhonemeDimension,
    db,
    *,
    allow_inject: bool,
) -> set[str]:
    """錨點音素選項：多讀音 union；allow_inject 控制是否 ensure。"""
    admission = resolve_admission(char)
    extract = _initials_from_entries if dimension == "initial" else _finals_from_entries
    options = extract(admission.entries)
    if options:
        return options

    rows = _db_rows_for_literal(char, db, allow_inject=allow_inject)
    result: set[str] = set()
    for row in rows:
        if dimension == "initial":
            initials = load_json_list(getattr(row, "initials", None))
            if initials:
                result.add(initials[0])
        else:
            finals = get_rhyme_finals(row)
            if finals:
                result.add(finals[0])
    return result


def equals_authoritative_row(literal: str, db, *, allow_inject: bool = True) -> Optional[Any]:
    """等號參考讀音：單列權威詞條，不 OR 比對。"""
    rows = _db_rows_for_literal(literal, db, allow_inject=allow_inject)
    return select_authoritative_pronunciation_row(rows)


def equals_ref_phoneme_parts(
    literal: str,
    dimension: PhonemeDimension,
    db,
    *,
    allow_inject: bool = True,
) -> Optional[list]:
    row = equals_authoritative_row(literal, db, allow_inject=allow_inject)
    if not row:
        return None
    if dimension == "final":
        parts = get_rhyme_finals(row)
        return parts if parts else None
    parts = load_json_list(getattr(row, "initials", None))
    return parts if parts else None


def final_options_for_char(ch: str, db, *, allow_inject: bool = True) -> set[str]:
    return anchor_phoneme_options(ch, "final", db, allow_inject=allow_inject)


def initial_options_for_char(ch: str, db, *, allow_inject: bool = True) -> set[str]:
    return anchor_phoneme_options(ch, "initial", db, allow_inject=allow_inject)


__all__ = [
    "anchor_phoneme_options",
    "equals_authoritative_row",
    "equals_ref_phoneme_parts",
    "final_options_for_char",
    "initial_options_for_char",
    "select_authoritative_pronunciation_row",
]