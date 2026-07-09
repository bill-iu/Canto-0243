"""缺字型查詢執行 — filters package (MF-5 F1–F5; Phase C PR2)."""
from __future__ import annotations

from app.services.position_match.filters.apply import (
    apply_match_spec,
    filter_candidates_by_match_spec,
)
from app.services.position_match.filters.f1_slot_code import (
    filter_words_by_code_and_mask,
    matches_code_positions,
    preferred_pronunciation_rows,
)
from app.services.position_match.mask_adapter import (
    dense_code_from_required,
    dense_code_from_spec,
    required_codes_from_digit_string,
    required_codes_from_spec,
)
from app.services.position_match.filters.f2_phoneme_anchor import (
    contextual_final_options_at_position,
    contextual_initial_options_at_position,
    matches_phoneme_at_position,
    word_passes_partial_initial_mask,
    word_passes_partial_rhyme_mask,
)
from app.services.position_match.filters.f3_letters import slot_constraint_matches
from app.services.position_match.filters.f4_equals import (
    build_final_options_at_positions,
    matches_equals_phoneme_span,
    matches_final_options,
    matches_hybrid_ref_chars,
    query_words_by_equals_spec,
    word_matches_last_final,
)

__all__ = [
    "apply_match_spec",
    "build_final_options_at_positions",
    "contextual_final_options_at_position",
    "contextual_initial_options_at_position",
    "dense_code_from_required",
    "dense_code_from_spec",
    "filter_candidates_by_match_spec",
    "filter_words_by_code_and_mask",
    "matches_code_positions",
    "matches_equals_phoneme_span",
    "matches_final_options",
    "matches_hybrid_ref_chars",
    "matches_phoneme_at_position",
    "preferred_pronunciation_rows",
    "query_words_by_equals_spec",
    "required_codes_from_digit_string",
    "required_codes_from_spec",
    "slot_constraint_matches",
    "word_matches_last_final",
    "word_passes_partial_initial_mask",
    "word_passes_partial_rhyme_mask",
]
