"""Unified normalizer for lexicon candidates across all supplement sources."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_validate import normalize_lexicon_candidate


class LexiconCandidateNormalizer:
    """Normalize raw literal/jyutping pairs into canonical LexiconCandidate rows."""

    def normalize_candidate(
        self,
        literal: str,
        jyutping: str,
        *,
        source_id: str,
        code: str | None = None,
    ) -> LexiconCandidate | None:
        if not literal or not jyutping:
            return None
        normalized = normalize_lexicon_candidate(literal, jyutping, code=code)
        if not normalized:
            return None
        char, jy, code_value = normalized
        return LexiconCandidate(char=char, jyutping=jy, code=code_value, sources=(source_id,))
