"""Stable ranking helpers for workbench semantic groups."""

from __future__ import annotations


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


__all__ = ["candidate_sort_key", "relation_index"]
