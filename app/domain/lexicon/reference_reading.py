"""參考字讀音解析 — CONTEXT § 參考字讀音解析 / 收錄決策。"""

from __future__ import annotations

from typing import Any, Literal, Optional, Set

from app.domain.lexicon.admission import resolve_admission
from app.domain.lexicon.port import default_word_inject_port
from app.domain.lexicon.ranking import authoritative_reading_sort_key
from app.domain.lexicon.word_row import get_rhyme_finals, get_word_jyutping, get_word_text
from app.models.word import Word
from app.lexicon.static_index import LexiconEntry
from app.utils.json_helpers import load_json_list
from app.utils.jyutping_codec import (
    expand_standalone_nasal_final_options,
    is_standalone_nasal_syllable_token,
    rhyme_final_index_keys_per_position,
    rhyme_finals_from_jyutping,
    split_jyutping,
)

PhonemeDimension = Literal["initial", "final"]


def _initials_from_entries(entries: list[LexiconEntry]) -> set[str]:
    options: set[str] = set()
    for ent in entries:
        if not ent.jyutping:
            continue
        token = ent.jyutping.split()[0]
        if is_standalone_nasal_syllable_token(token):
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
        for key_set in rhyme_final_index_keys_per_position(ent.jyutping):
            options |= set(key_set)
    return expand_standalone_nasal_final_options(options)


def select_authoritative_pronunciation_row(rows: list) -> Optional[Any]:
    """多讀音時選單列：pron_rank → Essay 詞頻 → 略過 aa 變體 → 粵拼序。"""
    if not rows:
        return None
    best = min(authoritative_reading_sort_key(row) for row in rows)
    for row in rows:
        if authoritative_reading_sort_key(row) == best:
            return row
    return rows[0]


def _db_rows_for_literal(literal: str, db, *, allow_inject: bool) -> list:
    rows = db.query(Word).filter(Word.char == literal).all()
    if rows or not allow_inject:
        return rows
    admission = resolve_admission(literal)
    if admission.can_inject:
        return default_word_inject_port().ensure_word_rows(db, literal)
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
            jyut = get_word_jyutping(row) or getattr(row, "jyutping", "") or ""
            token = jyut.split()[0] if jyut else ""
            if is_standalone_nasal_syllable_token(token):
                continue
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


def equals_authoritative_row_for_code(
    literal: str,
    code_prefix: str,
    mode: str,
    db,
    *,
    allow_inject: bool = True,
) -> Optional[Any]:
    """整詞等號 + 左碼前綴：參考讀音對齊該碼（詞級標音可補庫內 stale 列）。"""
    from app.lexicon.static_index import get_lexicon_entries
    from app.utils.jyutping_codec import get_code_variants

    variants = set(get_code_variants(code_prefix, mode))
    lexicon_hits = [e for e in get_lexicon_entries(literal) if e.code in variants]
    if lexicon_hits and allow_inject:
        default_word_inject_port().inject_lexicon_rows(db, literal, lexicon_hits)
    rows = db.query(Word).filter(Word.char == literal).all()
    matching = [r for r in rows if (getattr(r, "code", None) or "") in variants]
    if matching:
        return select_authoritative_pronunciation_row(matching)
    return None


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


def _phoneme_parts_suffix(row: Any, dimension: PhonemeDimension, suffix_len: int) -> Optional[list]:
    if suffix_len <= 0:
        return None
    if dimension == "final":
        parts = get_rhyme_finals(row)
    else:
        parts = load_json_list(getattr(row, "initials", None))
    if not parts or len(parts) < suffix_len:
        return None
    return parts[-suffix_len:]


def _rows_ending_with_literal(literal: str, db) -> list:
    rows = db.query(Word).filter(Word.char.like(f"%{literal}")).all()
    return [row for row in rows if get_word_text(row).endswith(literal)]


def suffix_aligned_ref_phoneme_parts(
    literal: str,
    dimension: PhonemeDimension,
    db,
    *,
    allow_inject: bool = True,
) -> Optional[list]:
    """前綴通配等號：後綴對齊讀音（長詞後綴優先）。"""
    ref_len = len(literal)
    if ref_len < 2:
        return equals_ref_phoneme_parts(literal, dimension, db, allow_inject=allow_inject)

    suffix_rows = _rows_ending_with_literal(literal, db)
    longer = [row for row in suffix_rows if len(get_word_text(row)) > ref_len]
    exact = [row for row in suffix_rows if len(get_word_text(row)) == ref_len]
    pool = longer or exact
    if not pool:
        return equals_ref_phoneme_parts(literal, dimension, db, allow_inject=allow_inject)

    row = select_authoritative_pronunciation_row(pool)
    if not row:
        return equals_ref_phoneme_parts(literal, dimension, db, allow_inject=allow_inject)
    return _phoneme_parts_suffix(row, dimension, ref_len)


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
    "suffix_aligned_ref_phoneme_parts",
]