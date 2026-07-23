"""Stable ranking helpers for workbench semantic groups."""

from __future__ import annotations

from app.domain.lexicon.ranking import search_result_sort_key


def relation_index(rows: list[dict]) -> dict[str, tuple[int, str | None]]:
    return {
        str(row.get("char")): (index, row.get("source"))
        for index, row in enumerate(rows)
        if row.get("char")
    }


def candidate_sort_key(candidate) -> tuple:
    return (
        candidate.source_rank,
        candidate.literal,
        candidate.jyutping,
    )


def sound_candidate_sort_key(candidate) -> tuple:
    """sound_only uses canonical search ranking with stable source tie-breaks."""
    return (
        *search_result_sort_key({"char": candidate.literal, "jyutping": candidate.jyutping}),
        candidate.source_rank,
        candidate.code,
    )


__all__ = ["candidate_sort_key", "relation_index", "sound_candidate_sort_key"]
