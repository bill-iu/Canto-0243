"""Merge lexicon candidates from SSOT sources by priority."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate


def merge_lexicon_candidates(
    layers: list[tuple[int, list[LexiconCandidate]]],
) -> list[LexiconCandidate]:
    """Higher source_rank first; same-layer multi readings kept; cross-layer claim blocks new jyutping."""
    ordered = sorted(layers, key=lambda item: -item[0])
    by_key: dict[tuple[str, str], LexiconCandidate] = {}
    claimed_multi: set[str] = set()

    for _rank, batch in ordered:
        layer_multi: set[str] = set()
        for c in batch:
            key = (c.char, c.jyutping)
            is_multi = len(c.char) >= 2
            if is_multi and c.char in claimed_multi:
                if key in by_key:
                    by_key[key] = _merge_sources(by_key[key], c)
                continue
            if key in by_key:
                by_key[key] = _merge_sources(by_key[key], c)
            else:
                by_key[key] = c
            if is_multi:
                layer_multi.add(c.char)
        claimed_multi |= layer_multi
    return list(by_key.values())


def _merge_sources(a: LexiconCandidate, b: LexiconCandidate) -> LexiconCandidate:
    merged = tuple(dict.fromkeys((*a.sources, *b.sources)))
    return LexiconCandidate(a.char, a.jyutping, a.code, merged)
