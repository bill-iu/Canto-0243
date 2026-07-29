"""MF-5 F4 helpers — equals phoneme storage / whole-word / hybrid match (line-cap split)."""
from __future__ import annotations

from typing import Any, Optional

from app.domain.lexicon.reference_reading import anchor_phoneme_options, equals_authoritative_row
from app.domain.lexicon.rhyme_match_profile import expand_final_options
from app.domain.lexicon.rhyme_profile_context import get_rhyme_profile
from app.services.position_match.spec import MatchSpec
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)


def ref_phoneme_parts_per_char(literal: str, dimension: str, db) -> Optional[list]:
    if len(literal) < 2:
        return None
    is_final = dimension == "final"
    parts = []
    for ch in literal:
        row = equals_authoritative_row(ch, db)
        if not row:
            return None
        slot_parts = get_rhyme_finals(row) if is_final else get_word_parts(row, "initials")
        if not slot_parts:
            return None
        parts.append(slot_parts[0])
    return parts


def build_final_options_at_positions(
    ref_chars: str,
    start_pos: int,
    width: int,
    db,
) -> list[Optional[set[str]]]:
    target_final_options: list[Optional[set[str]]] = [None] * width
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if 0 <= pos < width:
            options = anchor_phoneme_options(ch, "final", db, allow_inject=True)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    if not final_options:
        return True
    word_finals = get_rhyme_finals(word)
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def matches_final_options(word_finals: list, target_final_options: list[Optional[set[str]]]) -> bool:
    if len(word_finals) != len(target_final_options):
        return False
    profile = get_rhyme_profile()
    for idx, options in enumerate(target_final_options):
        if not options:
            continue
        expanded = expand_final_options(options, profile)
        if idx >= len(word_finals) or word_finals[idx] not in expanded:
            return False
    return True


def matches_hybrid_ref_chars(
    word_char: str,
    word_finals: list,
    ref_chars: str,
    start_pos: int,
    target_final_options: list[Optional[set[str]]],
) -> bool:
    width = len(target_final_options)
    if len(word_char) != width or len(word_finals) != width:
        return False
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if pos < 0 or pos >= width:
            return False
        if word_char[pos] == ch:
            continue
        options = target_final_options[pos]
        if options and word_finals[pos] in expand_final_options(options, get_rhyme_profile()):
            continue
        return False
    return True


def _word_stored_phoneme_json(word: Any, field: str):
    if isinstance(word, dict):
        return word.get(field)
    return getattr(word, field, None)


def phoneme_storage_key(word: Any, field: str) -> tuple:
    from app.domain.lexicon.phoneme_codec import decode_phoneme_field

    dim = "final" if field == "finals" else "initial"
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, list):
        return tuple(str(x) if x is not None else "" for x in raw)
    if isinstance(raw, str) and raw:
        return tuple(decode_phoneme_field(raw, dim))
    return ()


def phoneme_db_literal(word: Any, field: str) -> str:
    from app.domain.lexicon.phoneme_codec import encode_phoneme_list

    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, str):
        # already compact (or legacy JSON — equality will miss until migrate)
        return raw
    if isinstance(raw, list):
        dim = "final" if field == "finals" else "initial"
        return encode_phoneme_list([str(x) if x is not None else "" for x in raw], dim)
    return ""


def equals_length_bucket_candidates(
    width: int,
    dense_code: Optional[str],
    mode: str,
) -> Optional[list]:
    from app.services.position_match.filters.f1_slot_code import matches_code_positions
    from app.utils.word_cache import get_words_for_length, is_word_cache_ready

    if not is_word_cache_ready():
        return None
    candidates = get_words_for_length(width)
    if not dense_code:
        return candidates
    required = list(dense_code)
    return [
        w
        for w in candidates
        if matches_code_positions(get_word_sort_code(w) or "", required, mode)
    ]


def equals_whole_word_matches(
    spec: MatchSpec,
    db: Any,
    mode: str,
    *,
    target: Any | None,
    target_parts: list,
    is_final: bool,
) -> list[Any]:
    from app.models.word import Word
    from app.services.word_db_filters import apply_code_filter, length_filter
    from app.services.position_match.mask_adapter import dense_code_from_spec

    full_code = dense_code_from_spec(spec) or ""
    target_key = tuple(target_parts)
    cached = None if spec.candidate_scope == "complete" else equals_length_bucket_candidates(
        spec.width, full_code or None, mode
    )
    storage_field = "finals" if is_final else "initials"
    target_storage_key = phoneme_storage_key(target, storage_field) if target else target_key

    if cached is not None:
        pool = cached
        if target_storage_key:
            pool = [
                w
                for w in pool
                if phoneme_storage_key(w, storage_field) == target_storage_key
            ]
        if is_final:
            return [w for w in pool if tuple(get_rhyme_finals(w)) == target_key]
        return [w for w in pool if tuple(get_word_parts(w, "initials")) == target_key]

    query = db.query(Word).filter(length_filter(spec.width))
    if full_code:
        query = apply_code_filter(query, full_code, mode)
    if is_final:
        if target:
            db_literal = phoneme_db_literal(target, "finals")
        else:
            from app.domain.lexicon.phoneme_codec import encode_phoneme_list
            db_literal = encode_phoneme_list(target_parts, "final")
        if db_literal:
            query = query.filter(Word.finals == db_literal)
        return [
            w
            for w in query.all()
            if tuple(get_rhyme_finals(w)) == target_key
        ]
    if target:
        db_literal = phoneme_db_literal(target, "initials")
    else:
        from app.domain.lexicon.phoneme_codec import encode_phoneme_list
        db_literal = encode_phoneme_list(target_parts, "initial")
    if db_literal:
        query = query.filter(Word.initials == db_literal)
    return query.all()
