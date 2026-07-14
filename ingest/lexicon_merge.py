"""Merge lexicon candidates from SSOT sources by priority."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate


def merge_lexicon_candidates(
    layers: list[tuple[int, list[LexiconCandidate]]],
) -> list[LexiconCandidate]:
    """Higher source_rank first; same-layer multi readings kept.

    Cross-layer: lower sources may *add* a new (literal, jyutping) not yet seen;
    they must not rewrite an existing pair (only merge provenance flags).
    """
    ordered = sorted(layers, key=lambda item: -item[0])
    by_key: dict[tuple[str, str], LexiconCandidate] = {}

    for _rank, batch in ordered:
        for c in batch:
            key = (c.char, c.jyutping)
            if key in by_key:
                by_key[key] = _merge_sources(by_key[key], c)
            else:
                by_key[key] = c
    return list(by_key.values())


def _merge_sources(a: LexiconCandidate, b: LexiconCandidate) -> LexiconCandidate:
    merged = tuple(dict.fromkeys((*a.sources, *b.sources)))
    return LexiconCandidate(a.char, a.jyutping, a.code, merged)
