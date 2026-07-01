"""Merge lexicon candidates from SSOT sources by priority."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate


def merge_lexicon_candidates(
    layers: list[tuple[int, list[LexiconCandidate]]],
) -> list[LexiconCandidate]:
    """Higher source_rank first; multi-char literals claimed by higher source block lower."""
    ordered = sorted(layers, key=lambda item: -item[0])
    by_key: dict[tuple[str, str], LexiconCandidate] = {}
    claimed_multi: set[str] = set()

    for _rank, batch in ordered:
        for c in batch:
            key = (c.char, c.jyutping)
            if len(c.char) >= 2 and c.char in claimed_multi:
                if key in by_key:
                    by_key[key] = _merge_sources(by_key[key], c)
                continue
            if key in by_key:
                by_key[key] = _merge_sources(by_key[key], c)
            else:
                by_key[key] = c
                if len(c.char) >= 2:
                    claimed_multi.add(c.char)
    return list(by_key.values())


def _merge_sources(a: LexiconCandidate, b: LexiconCandidate) -> LexiconCandidate:
    merged = tuple(dict.fromkeys((*a.sources, *b.sources)))
    return LexiconCandidate(a.char, a.jyutping, a.code, merged)
