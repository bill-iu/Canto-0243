"""MF-5 F4 — equals span / 碼夾等號 execution."""
from __future__ import annotations

from typing import Any

from app.domain.lexicon.rhyme_match_profile import finals_compatible
from app.domain.lexicon.rhyme_profile_context import get_rhyme_profile
from app.services._generated.candidate_source_policy import CANDIDATE_FALLBACK_LIMIT
from app.services.position_match.filters.f4_equals_helpers import (
    build_final_options_at_positions,
    equals_length_bucket_candidates,
    equals_whole_word_matches,
    matches_hybrid_ref_chars,
    matches_final_options,
    ref_phoneme_parts_per_char,
    word_matches_last_final,
)
from app.services.position_match.spec import MatchSpec
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)

# Re-export helpers used via filters package / tests.
__all__ = [
    "build_final_options_at_positions",
    "matches_equals_phoneme_span",
    "matches_final_options",
    "matches_hybrid_ref_chars",
    "query_words_by_equals_spec",
    "word_matches_last_final",
]


def matches_equals_phoneme_span(
    word,
    ref_parts: list,
    start_pos: int,
    *,
    phoneme_anchor_only: bool,
    ref_literal: str,
    dimension: str,
) -> bool:
    """碼夾等號 span：參考詞韻母比對（受 韻母比對檔 影響）。"""
    char_text = get_word_text(word)
    if not phoneme_anchor_only and ref_literal and ref_literal not in char_text:
        return False
    field = "finals" if dimension == "final" else "initials"
    is_final = dimension == "final"
    word_parts = get_rhyme_finals(word) if is_final else get_word_parts(word, field)
    if not word_parts:
        return False
    profile = get_rhyme_profile()
    for i in range(len(ref_parts)):
        pos = start_pos + i
        if pos >= len(word_parts):
            return False
        ref = ref_parts[i]
        if not ref:
            continue
        if is_final:
            if not finals_compatible(ref, word_parts[pos], profile):
                return False
        elif ref != word_parts[pos]:
            return False
    return True


def query_words_by_equals_spec(spec: MatchSpec, db: Any, mode: str = "m1") -> list[Any]:
    """等號／碼夾等號查詢：候選解析 + span 比對（ADR-0004 收斂至 filters）。"""
    from app.domain.lexicon.reference_reading import (
        equals_authoritative_row,
        equals_authoritative_row_for_code,
        suffix_aligned_ref_phoneme_parts,
    )
    from app.models.word import Word
    from app.services.word_db_filters import apply_code_filter, length_filter
    from app.services.position_match.mask_adapter import dense_code_from_spec

    if not spec.equals_span:
        return []

    span = spec.equals_span
    assert span is not None
    is_final = span.dimension == "final"
    dimension = "final" if is_final else "initial"
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
            target_parts = ref_phoneme_parts_per_char(span.ref_literal, dimension, db)
            if not target_parts:
                return []

    query = db.query(Word)
    query = apply_code_filter(query, full_code, mode)
    query = query.filter(length_filter(spec.width))

    if span.whole_word:
        if is_final:
            from app.utils.word_cache import get_whole_word_loose_final_intersect

            profile = get_rhyme_profile()
            if profile != "exact":
                # ADR-0079: index ∪/∩; F1 fallback = length bucket scan + span filter
                indexed = get_whole_word_loose_final_intersect(
                    spec.width, target_parts, profile,
                )
                if indexed is not None:
                    pool = indexed
                    if full_code:
                        from app.services.position_match.filters.f1_slot_code import (
                            matches_code_positions,
                        )

                        required = list(full_code)
                        pool = [
                            w
                            for w in pool
                            if matches_code_positions(
                                get_word_sort_code(w) or "", required, mode,
                            )
                        ]
                    return [
                        w
                        for w in pool
                        if matches_equals_phoneme_span(
                            w,
                            target_parts,
                            span.start_pos,
                            phoneme_anchor_only=span.phoneme_anchor_only,
                            ref_literal=span.ref_literal,
                            dimension=span.dimension,
                        )
                    ]
                cached = (
                    None
                    if spec.candidate_scope == "complete"
                    else equals_length_bucket_candidates(
                        spec.width, full_code or None, mode,
                    )
                )
                pool = cached if cached is not None else query.all()
                return [
                    w
                    for w in pool
                    if matches_equals_phoneme_span(
                        w,
                        target_parts,
                        span.start_pos,
                        phoneme_anchor_only=span.phoneme_anchor_only,
                        ref_literal=span.ref_literal,
                        dimension=span.dimension,
                    )
                ]
        return equals_whole_word_matches(
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
        cached = None if spec.candidate_scope == "complete" else equals_length_bucket_candidates(
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
        bucket = None if spec.candidate_scope == "complete" else equals_length_bucket_candidates(
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
