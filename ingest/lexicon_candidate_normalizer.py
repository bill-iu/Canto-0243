"""Unified normalizer for lexicon candidates across all supplement sources."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_validate import normalize_lexicon_candidate


class DefaultLexiconCandidateStrategy:
    """Default strategy for normalizing a literal/jyutping pair."""

    def should_accept(self, literal: str, jyutping: str) -> bool:
        return bool(literal and jyutping)

    def build_code(self, literal: str, jyutping: str, *, code: str | None = None) -> str:
        normalized = normalize_lexicon_candidate(literal, jyutping, code=code)
        return normalized[2] if normalized else ""


class LexiconCandidateNormalizer:
    """Normalize raw literal/jyutping pairs into canonical LexiconCandidate rows."""

    def __init__(self, *, strategy: DefaultLexiconCandidateStrategy | None = None) -> None:
        self.strategy = strategy or DefaultLexiconCandidateStrategy()

    def normalize_candidate(
        self,
        literal: str,
        jyutping: str,
        *,
        source_id: str,
        code: str | None = None,
    ) -> LexiconCandidate | None:
        if not self.strategy.should_accept(literal, jyutping):
            return None
        normalized = normalize_lexicon_candidate(literal, jyutping, code=code)
        if not normalized:
            return None
        char, jy, _ = normalized
        code_value = self.strategy.build_code(literal, jyutping, code=code)
        if not code_value:
            return None
        return LexiconCandidate(char=char, jyutping=jy, code=code_value, sources=(source_id,))
