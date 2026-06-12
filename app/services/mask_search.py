from __future__ import annotations

import json
import re
from typing import List, Optional

from utils import get_code_variants, get_words_for_length, load_json_list

from app.models.word import Word
from app.services.phoneme_lookup import final_options_for_char, initial_options_for_char
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_query_parser import (
    mask_char_glob_pattern,
    matches_mask_literal_chars,
    parse_mask_query,
)

# Phase 2.1：位置匹配核心 helper 已全部搬移至 position_match.py
# 呼叫端透過 import 使用，行為等價。
from app.services.position_match import (
    PositionMatchEngine,
    MatchSpec,
    SlotConstraint,
    filter_words_by_code_and_mask,
    matches_code_positions,
    matches_phoneme_at_position,
    get_length_candidates,
    get_candidates_for_length,
    build_final_options_at_positions,
    word_matches_last_final,
    matches_final_options,
    matches_hybrid_ref_chars,
    mask_priority_key,
)
from app.services.word_serializer import (
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
    serialize_page,
)

# app/services/position_match.py（Phase 2.1）。由新模組提供實作，呼叫站點不變。
# get_length_candidates 與 get_candidates_for_length 亦已搬移。


def handle_rhyme_anchor_query(parsed, mode: str, limit: int, offset: int, db):
    """Thin adapter (Phase 2.3 normalized): rely on parsed.to_match_spec() for canonical MatchSpec.
    Pre-candidate logic + engine dispatch + sort/serialize stay minimal (adapter role).
    """
    spec = parsed.to_match_spec()
    width = spec.width
    mask = spec.mask
    candidates, _ = get_length_candidates(db, width, mask)
    # Thin: call engine with pre-filtered candidates (preserves original cache mask pre / DB GLOB)
    filtered = PositionMatchEngine().match(spec, None, db, mode, pre_candidates=candidates)
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_code_tail_query(parsed, mode: str, limit: int, offset: int, db):
    """Thin adapter (Phase 2.3 normalized): use parsed.to_match_spec() (encapsulates literal/phoneme + mask)."""
    spec = parsed.to_match_spec()
    width = spec.width
    mask = spec.mask
    candidates, _ = get_length_candidates(db, width, mask)
    # Thin: call engine with pre-filtered candidates (behavior identical)
    filtered = PositionMatchEngine().match(spec, None, db, mode, pre_candidates=candidates)
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_at_tail_query(parsed, mode: str, limit: int, offset: int, db):
    """Thin adapter (Phase 2.3 normalized): use parsed.to_match_spec()."""
    spec = parsed.to_match_spec()
    width = spec.width
    mask = spec.mask
    candidates, _ = get_length_candidates(db, width, mask)
    # Thin: call engine with pre-filtered candidates (behavior identical)
    filtered = PositionMatchEngine().match(spec, None, db, mode, pre_candidates=candidates)
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


# build_final_options_at_positions 已搬移至 position_match.py


# word_matches_last_final 已搬移至 position_match.py


# matches_code_positions 已搬移至 app/services/position_match.py（Phase 2.1）
# 此處保留 import 以維持呼叫站點不變（由 position_match 提供實作）。


# matches_final_options 已搬移至 position_match.py


# matches_hybrid_ref_chars 已搬移至 position_match.py


# mask_priority_key 已搬移至 position_match.py


def handle_hybrid_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):  # untyped db to avoid FastAPI treating it as a response field during module import
    """Thin layer adapter: only responsible for parsing q to MatchSpec and calling engine.
    Keep the special candidate get for pre (to match original pre-filter behavior), pass to engine for matching.
    """
    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if not hybrid_match:
        return []

    num_prefix = hybrid_match.group(1)
    ref_chars = hybrid_match.group(2)
    num_suffix = hybrid_match.group(3)

    full_code = num_prefix + num_suffix
    ref_pos = max(0, len(num_prefix) - 1)

    spec = MatchSpec(
        width=len(full_code),
        code_prefix=full_code,
        hybrid_ref_chars=ref_chars,
        hybrid_ref_pos=ref_pos,
    )

    candidates, used_cache = get_candidates_for_length(
        db, len(full_code), code=full_code, mode=mode,
    )
    filtered = PositionMatchEngine().match(spec, None, db, mode, pre_candidates=candidates)
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_mask_wildcard_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):
    """Thin layer adapter: only responsible for parsing q to MatchSpec and calling engine.
    Keep the special pre-filter logic for candidates (to match original behavior for cache/db), pass pre to engine.
    Engine applies the filter on pre list.
    Sort with priority after.
    """
    mask = q
    expected_len, required_codes, literal_positions = parse_mask_query(mask)
    if expected_len == 0:
        return []

    spec = MatchSpec(
        width=expected_len,
        code_prefix=code or "",
        literal_priority=True,
        mask=mask,
    )
    # No literal_char slots (mask canto literals are handled via the mask param + matches_mask_literal_chars to avoid
    # polluting the single-tail literal_char special case in filter).
    # But DO populate code_digit slots for any digits in the mask (e.g. "門0", "好23"). These are now honored
    # in filter_words_by_code_and_mask (and engine reconstruction can use them too).
    for i, ch in enumerate(mask):
        if ch.isdigit():
            spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=ch))

    glob_pat = mask_char_glob_pattern(mask)
    candidates = get_words_for_length(expected_len)
    used_cache = bool(candidates)
    if used_cache:
        candidates = [
            w for w in candidates
            if matches_mask_literal_chars(get_word_text(w), mask)
        ]
    else:
        query = db.query(Word).filter(
            length_filter(expected_len),
            Word.char.op("GLOB")(glob_pat),
        )
        code_filter = "".join(required_codes) if all(req is not None for req in required_codes) else None
        if code_filter:
            query = apply_code_filter(query, code_filter, mode)
        candidates = query.order_by(Word.char, Word.jyutping).all()

    filtered = PositionMatchEngine().match(spec, None, db, mode, pre_candidates=candidates)
    filtered.sort(key=lambda item: mask_priority_key(item, literal_positions))
    return serialize_page(filtered, offset, limit)
