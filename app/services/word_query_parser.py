"""word_query_parser — facade re-export（#3 收尾；實作見 query_lexer／query_grammar）。"""
from __future__ import annotations

from app.services.query_grammar.equals import (
    hybrid_query_from_tail_equals,
    is_framed_equals_query,
    is_hybrid_tail_equals_alias,
)
from app.services.query_grammar.mask import (
    build_mask_from_slots,
    looks_like_mask_query,
    parse_mask_query,
)
from app.services.query_grammar.relation import parse_relation_syntax
from app.services.query_grammar.rhyme import (
    parse_code_ref_middle_rhyme_query,
    parse_code_ref_rhyme_contradiction_hint,
    parse_double_wildcard_initial_query,
    parse_double_wildcard_rhyme_query,
    parse_rhyme_anchor_query,
    parse_triple_rhyme_anchor_query,
)
from app.services.query_grammar.serial import (
    PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT,
    PURE_CHARS_SERIAL_HINT,
    parse_prefix_wildcard_equals_query,
    parse_pure_chars_serial_hint,
    parse_serial_phoneme_anchor_query,
    prefix_wildcard_equals_missing_eq_hint,
)
from app.services.query_grammar.plus import (
    mask_from_canonical_plus_query,
    normalize_canonical_plus_query,
    parse_at_tail_query,
    parse_code_tail_query,
    parse_plus_anchor_query,
)
from app.services.query_grammar.wca import (
    looks_like_wildcard_code_anchor_query,
    parse_wildcard_code_anchor_query,
)
from app.services.query_lexer import (
    normalize_code_tail_separators,
    normalize_jyutping_slot_connectors,
    normalize_query_syntax,
    normalize_search_query,
    normalize_search_query_core,
    slot_connector_syntax_error,
)
from app.services.query_tokens import (
    CODE_TAIL_MIDDLE,
    CONSECUTIVE_SLOT_CONNECTOR_HINT,
    DIGIT_AFTER_SLOT_CONNECTOR_HINT,
    WILDCARD_CHARS,
    is_wildcard_char,
)

__all__ = [
    "CODE_TAIL_MIDDLE",
    "CONSECUTIVE_SLOT_CONNECTOR_HINT",
    "DIGIT_AFTER_SLOT_CONNECTOR_HINT",
    "PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT",
    "PURE_CHARS_SERIAL_HINT",
    "WILDCARD_CHARS",
    "build_mask_from_slots",
    "hybrid_query_from_tail_equals",
    "is_framed_equals_query",
    "is_hybrid_tail_equals_alias",
    "is_wildcard_char",
    "looks_like_mask_query",
    "looks_like_wildcard_code_anchor_query",
    "mask_from_canonical_plus_query",
    "normalize_canonical_plus_query",
    "normalize_code_tail_separators",
    "normalize_jyutping_slot_connectors",
    "normalize_query_syntax",
    "normalize_search_query",
    "normalize_search_query_core",
    "parse_at_tail_query",
    "parse_code_ref_middle_rhyme_query",
    "parse_code_ref_rhyme_contradiction_hint",
    "parse_code_tail_query",
    "parse_double_wildcard_initial_query",
    "parse_double_wildcard_rhyme_query",
    "parse_mask_query",
    "parse_prefix_wildcard_equals_query",
    "parse_pure_chars_serial_hint",
    "parse_relation_syntax",
    "parse_rhyme_anchor_query",
    "parse_serial_phoneme_anchor_query",
    "parse_plus_anchor_query",
    "parse_triple_rhyme_anchor_query",
    "parse_wildcard_code_anchor_query",
    "prefix_wildcard_equals_missing_eq_hint",
    "slot_connector_syntax_error",
]
