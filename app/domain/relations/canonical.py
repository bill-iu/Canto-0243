"""Canonical ordering for undirected word_relations (smaller word id first)."""
from __future__ import annotations

from typing import Tuple


def canonical_word_ids(a: int, b: int) -> Tuple[int, int]:
    """Always store the lower word id in word_id column."""
    if a <= b:
        return a, b
    return b, a


def relation_storage_key(word_id: int, related_id: int, relation_type: str) -> Tuple[int, int, str]:
    w, r = canonical_word_ids(word_id, related_id)
    return w, r, relation_type


def canonical_relation_dict(rel: dict) -> dict:
    w, r = canonical_word_ids(int(rel["word_id"]), int(rel["related_id"]))
    out = dict(rel)
    out["word_id"] = w
    out["related_id"] = r
    return out
