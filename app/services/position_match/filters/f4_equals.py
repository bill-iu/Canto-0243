"""MF-5 F4 — equals span / 碼夾等號 execution."""
from __future__ import annotations
from typing import Any, Optional
from app.domain.lexicon.reference_reading import anchor_phoneme_options, equals_authoritative_row
from app.services._generated.candidate_source_policy import CANDIDATE_FALLBACK_LIMIT
from app.services.position_match.spec import MatchSpec, get_equals_span
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)

def matches_equals_phoneme_span(
    word,
    ref_parts: list,
    start_pos: int,
    *,
    phoneme_anchor_only: bool,
    ref_literal: str,
    dimension: str,
) -> bool:
    """碼夾等號 span：參考詞 JSON 逐格精確比對（非 options OR）。"""
    char_text = get_word_text(word)
    if not phoneme_anchor_only and ref_literal and ref_literal not in char_text:
        return False
    field = "finals" if dimension == "final" else "initials"
    word_parts = get_rhyme_finals(word) if dimension == "final" else get_word_parts(word, field)
    if not word_parts:
        return False
    for i in range(len(ref_parts)):
        pos = start_pos + i
        if pos >= len(word_parts):
            return False
        if ref_parts[i] and ref_parts[i] != word_parts[pos]:
            return False
    return True

def _ref_phoneme_parts_per_char(literal: str, dimension: str, db) -> Optional[list]:
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
    for idx, options in enumerate(target_final_options):
        if not options:
            continue
        if idx >= len(word_finals) or word_finals[idx] not in options:
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
        if options and word_finals[pos] in options:
            continue
        return False
    return True

def _word_stored_phoneme_json(word: Any, field: str):
    if isinstance(word, dict):
        return word.get(field)
    return getattr(word, field, None)

def _phoneme_storage_key(word: Any, field: str) -> tuple:
    from app.domain.lexicon.phoneme_codec import decode_phoneme_field

    dim = "final" if field == "finals" else "initial"
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, list):
        return tuple(str(x) if x is not None else "" for x in raw)
    if isinstance(raw, str) and raw:
        return tuple(decode_phoneme_field(raw, dim))
    return ()

def _phoneme_db_literal(word: Any, field: str) -> str:
    from app.domain.lexicon.phoneme_codec import encode_phoneme_list

    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, str):
        # already compact (or legacy JSON — equality will miss until migrate)
        return raw
    if isinstance(raw, list):
        dim = "final" if field == "finals" else "initial"
        return encode_phoneme_list([str(x) if x is not None else "" for x in raw], dim)
    return ""

def _equals_length_bucket_candidates(
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

def _equals_whole_word_matches(
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
    cached = None if spec.candidate_scope == "complete" else _equals_length_bucket_candidates(
        spec.width, full_code or None, mode
    )
    storage_field = "finals" if is_final else "initials"
    target_storage_key = _phoneme_storage_key(target, storage_field) if target else target_key

    if cached is not None:
        pool = cached
        if target_storage_key:
            pool = [
                w
                for w in pool
                if _phoneme_storage_key(w, storage_field) == target_storage_key
            ]
        if is_final:
            return [w for w in pool if tuple(get_rhyme_finals(w)) == target_key]
        return [w for w in pool if tuple(get_word_parts(w, "initials")) == target_key]

    query = db.query(Word).filter(length_filter(spec.width))
    if full_code:
        query = apply_code_filter(query, full_code, mode)
    if is_final:
        if target:
            db_literal = _phoneme_db_literal(target, "finals")
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
        db_literal = _phoneme_db_literal(target, "initials")
    else:
        from app.domain.lexicon.phoneme_codec import encode_phoneme_list
        db_literal = encode_phoneme_list(target_parts, "initial")
    if db_literal:
        query = query.filter(Word.initials == db_literal)
    return query.all()

def query_words_by_equals_spec(spec: MatchSpec, db: Any, mode: str = "m1") -> list[Any]:
    """等號／碼夾等號查詢：候選解析 + span 比對（ADR-0004 收斂至 filters）。"""
    from app.domain.lexicon.reference_reading import (
        equals_authoritative_row,
        equals_authoritative_row_for_code,
        suffix_aligned_ref_phoneme_parts,
    )
    from app.models.word import Word
    from app.services.word_db_filters import apply_code_filter, length_filter

    if not spec.equals_span:
        return []

    span = spec.equals_span
    assert span is not None
    is_final = span.dimension == "final"
    dimension = "final" if is_final else "initial"
    from app.services.position_match.mask_adapter import dense_code_from_spec

    prefix_wildcard = span.start_pos == 1 and span.phoneme_anchor_only
    full_code = dense_code_from_spec(spec) or ""

    if span.ref_jyutping:
        from app.utils.jyutping_codec import rhyme_finals_from_jyutping, split_jyutping_parts

        initials, _finals, _tones = split_jyutping_parts(span.ref_jyutping)
        target_parts = rhyme_finals_from_jyutping(span.ref_jyutping) if is_final else initials
        if len(target_parts) != len(span.ref_literal):
            return []
        target = None
    elif prefix_wildcard:
        target_parts = suffix_aligned_ref_phoneme_parts(
            span.ref_literal, dimension, db, allow_inject=True,
        )
        if not target_parts:
            return []
        target = None
    else:
        if span.whole_word and full_code and spec.width == 4:
            # CONTEXT § 等號查詢：四字先用左碼對齊參考讀音；短詞只用權威列
            target = equals_authoritative_row_for_code(
                span.ref_literal, full_code, mode, db, allow_inject=True,
            )
            if target is None:
                target = equals_authoritative_row(
                    span.ref_literal, db, allow_inject=True,
                )
        else:
            target = equals_authoritative_row(span.ref_literal, db, allow_inject=True)
        if target:
            target_parts = (
                get_rhyme_finals(target)
                if is_final
                else get_word_parts(target, "initials")
            )
            if not target_parts:
                return []
        else:
            target_parts = _ref_phoneme_parts_per_char(span.ref_literal, dimension, db)
            if not target_parts:
                return []

    query = db.query(Word)
    query = apply_code_filter(query, full_code, mode)
    query = query.filter(length_filter(spec.width))

    if span.whole_word:
        return _equals_whole_word_matches(
            spec,
            db,
            mode,
            target=target,
            target_parts=target_parts,
            is_final=is_final,
        )

    # Dense full_code already narrows; LIMIT before phoneme filter drops hits when
    # m1 variants expand past CANDIDATE_FALLBACK_LIMIT (e.g. 9太=2 → 解毒).
    if prefix_wildcard or full_code:
        cached = None if spec.candidate_scope == "complete" else _equals_length_bucket_candidates(
            spec.width, full_code or None, mode
        )
        candidates = cached if cached is not None else query.all()
    else:
        candidates = query.limit(CANDIDATE_FALLBACK_LIMIT).all()

    tail_rhyme_union = (
        is_final
        and full_code
        and not span.whole_word
        and not span.phoneme_anchor_only
    )
    if tail_rhyme_union:
        bucket = None if spec.candidate_scope == "complete" else _equals_length_bucket_candidates(
            spec.width, full_code or None, mode
        )
        if bucket is not None:
            pool = bucket
        else:
            from app.services.position_match.sources import get_candidates_for_length

            # Prefer code-narrowed bucket; cap when no dense code (Portable hang)
            pool, _ = get_candidates_for_length(
                db,
                spec.width,
                code=full_code or None,
                mode=mode,
                fallback_limit=None if full_code else CANDIDATE_FALLBACK_LIMIT,
            )
        target_final_options = build_final_options_at_positions(
            span.ref_literal, span.start_pos, spec.width, db
        )
        return [
            word
            for word in pool
            if matches_hybrid_ref_chars(
                get_word_text(word),
                get_rhyme_finals(word),
                span.ref_literal,
                span.start_pos,
                target_final_options,
            )
        ]

    return [
        word
        for word in candidates
        if matches_equals_phoneme_span(
            word,
            target_parts,
            span.start_pos,
            phoneme_anchor_only=span.phoneme_anchor_only,
            ref_literal=span.ref_literal,
            dimension=span.dimension,
        )
    ]
