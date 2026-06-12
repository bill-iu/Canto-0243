from __future__ import annotations

import re
from typing import Optional

from app.services.position_match import (
    LengthCodeCandidateSource,
    LengthMaskCandidateSource,
    MaskWildcardCandidateSource,
    MatchSpec,
    PositionMatchEngine,
    build_final_options_at_positions,
    mask_priority_key,
    matches_hybrid_ref_chars,
    run_position_query,
    word_matches_last_final,
)
from app.services.word_serializer import get_word_text

# Re-export for word_search_service compound-ant path
__all__ = [
    "handle_rhyme_anchor_query",
    "handle_code_tail_query",
    "handle_at_tail_query",
    "handle_hybrid_syntax",
    "handle_mask_wildcard_query",
    "word_matches_last_final",
    "matches_hybrid_ref_chars",
    "build_final_options_at_positions",
    "mask_priority_key",
]


def handle_rhyme_anchor_query(parsed, mode: str, limit: int, offset: int, db):
    spec = parsed.to_match_spec()
    source = LengthMaskCandidateSource(db, spec.mask)
    return run_position_query(spec, db, mode, limit, offset, source=source)


def handle_code_tail_query(parsed, mode: str, limit: int, offset: int, db):
    spec = parsed.to_match_spec()
    source = LengthMaskCandidateSource(db, spec.mask)
    return run_position_query(spec, db, mode, limit, offset, source=source)


def handle_at_tail_query(parsed, mode: str, limit: int, offset: int, db):
    spec = parsed.to_match_spec()
    source = LengthMaskCandidateSource(db, spec.mask)
    return run_position_query(spec, db, mode, limit, offset, source=source)


def handle_hybrid_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):
    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if not hybrid_match:
        return []

    num_prefix = hybrid_match.group(1)
    ref_chars = hybrid_match.group(2)
    num_suffix = hybrid_match.group(3)
    full_code = num_prefix + num_suffix

    spec = MatchSpec(
        width=len(full_code),
        code_prefix=full_code,
        hybrid_ref_chars=ref_chars,
        hybrid_ref_pos=max(0, len(num_prefix) - 1),
    )
    source = LengthCodeCandidateSource(db, code=full_code, mode=mode)
    return run_position_query(spec, db, mode, limit, offset, source=source)


def handle_mask_wildcard_query(parsed, code: Optional[str], mode: str, limit: int, offset: int, db):
    spec = parsed.to_match_spec()
    if spec.width == 0:
        return []
    if code:
        spec.code_prefix = code

    literal_positions = spec.extra.get("literal_positions", [])
    source = MaskWildcardCandidateSource(db, spec.mask, mode=mode, query_code=spec.code_prefix)
    sort_key = lambda w: mask_priority_key(w, literal_positions)
    return run_position_query(spec, db, mode, limit, offset, source=source, sort_key=sort_key)
