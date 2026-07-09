"""Undirected syn neighbor cap (ADR-0039 S1 CAP-U@20)."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Sequence, TypeVar, Union

from app.domain.relations.bulk_insert import RelationRecord, RelationTuple

# per-endpoint undirected neighbor limit for syn edges
SYN_NEIGHBOR_CAP = 20

_SOURCE_PREF = {"cilin": 0, "guotong": 1, "compound_ant": 2, "manual": 3}

T = TypeVar("T")


def _as_tuple(row: Union[RelationRecord, RelationTuple]) -> RelationTuple:
    if isinstance(row, RelationRecord):
        return (
            row.word_id,
            row.related_id,
            row.relation_type,
            row.score,
            row.source,
            row.group_codes,
        )
    return row


def cap_undirected_syn_tuples(
    rows: Sequence[Union[RelationRecord, RelationTuple]],
    *,
    k: int = SYN_NEIGHBOR_CAP,
) -> List[RelationTuple]:
    """
    Keep non-syn rows; for syn, greedily keep edges so each endpoint has ≤k neighbors.
    Prefer higher score, then cilin over guotong.
    """
    syn: List[RelationTuple] = []
    other: List[RelationTuple] = []
    for raw in rows:
        t = _as_tuple(raw)
        if t[2] == "syn":
            syn.append(t)
        else:
            other.append(t)

    syn.sort(
        key=lambda e: (
            -(float(e[3]) if e[3] is not None else 0.0),
            _SOURCE_PREF.get(e[4] or "", 9),
            e[0],
            e[1],
        )
    )
    deg: dict[int, int] = defaultdict(int)
    kept: List[RelationTuple] = []
    for w, r, rtype, score, src, gc in syn:
        if deg[w] >= k or deg[r] >= k:
            continue
        deg[w] += 1
        deg[r] += 1
        kept.append((w, r, rtype, score, src, gc))
    return other + kept


__all__ = ["SYN_NEIGHBOR_CAP", "cap_undirected_syn_tuples"]
