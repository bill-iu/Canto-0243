"""Lexicon build candidates (pre-persist word rows)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LexiconCandidate:
    char: str
    jyutping: str
    code: str
    sources: tuple[str, ...] = ()

    def with_reading(self, jyutping: str, code: str) -> LexiconCandidate:
        return LexiconCandidate(self.char, jyutping, code, self.sources)
