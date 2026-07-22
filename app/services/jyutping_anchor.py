"""粵拼錨：缺字家族內拉丁錨解析與比對（CONTEXT § 粵拼錨）。

實作分佈於 jyutping_anchor_parse（解析／分類）與 jyutping_anchor_match（比對／MatchSpec）。
"""
from app.services.jyutping_anchor_match import (
    build_jyutping_dual_match_specs,
    matches_jyutping_anchor_at_position,
    rhyme_letters_resolve_ok,
    to_match_spec,
)
from app.services.jyutping_anchor_parse import (
    AMBIGUOUS_PHONEME_LETTERS,
    INITIAL_CLUSTERS,
    STANDALONE_NG,
    VOWEL_RHYME_LETTERS,
    AnchorKind,
    classify_latin_anchor,
    default_syllable_letters_for_anchor_char,
    is_jyutping_anchor_mask_query,
    normalize_hanzi_dollar_syllable_anchors,
    normalize_rhyme_letters,
    parse_jyutping_anchor_query,
)

__all__ = [
    "AMBIGUOUS_PHONEME_LETTERS",
    "INITIAL_CLUSTERS",
    "STANDALONE_NG",
    "VOWEL_RHYME_LETTERS",
    "AnchorKind",
    "build_jyutping_dual_match_specs",
    "classify_latin_anchor",
    "default_syllable_letters_for_anchor_char",
    "is_jyutping_anchor_mask_query",
    "matches_jyutping_anchor_at_position",
    "normalize_hanzi_dollar_syllable_anchors",
    "normalize_rhyme_letters",
    "parse_jyutping_anchor_query",
    "rhyme_letters_resolve_ok",
    "to_match_spec",
]
