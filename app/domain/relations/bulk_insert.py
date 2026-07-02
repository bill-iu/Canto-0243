"""Bulk word_relations insert: in-memory records, 2000-row transactions, conflict drop."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids

RelationTuple = Tuple[int, int, str, Optional[float], Optional[str], Optional[str]]
CHUNK_SIZE = 2000


@dataclass(frozen=True, slots=True)
class RelationRecord:
    """In-memory relation row before chunked DB insert."""

    word_id: int
    related_id: int
    relation_type: str
    score: Optional[float] = None
    source: Optional[str] = None
    group_codes: Optional[str] = None

    def as_tuple(self) -> RelationTuple:
        return (
            self.word_id,
            self.related_id,
            self.relation_type,
            self.score,
            self.source,
            self.group_codes,
        )

    def to_param(self) -> dict:
        return {
            "w": self.word_id,
            "r": self.related_id,
            "t": self.relation_type,
            "s": self.score,
            "src": self.source,
            "gc": self.group_codes,
        }


def normalize_relation_tuple(
    word_id: int,
    related_id: int,
    relation_type: str,
    score: Optional[float] = None,
    source: Optional[str] = None,
    group_codes: Optional[str] = None,
) -> Optional[RelationTuple]:
    w, r = canonical_word_ids(int(word_id), int(related_id))
    if w == r:
        return None
    rtype = str(relation_type or "").strip()
    if rtype not in ("syn", "ant", "semantic_related"):
        return None
    src = (str(source)[:32] if source else None)
    return (w, r, rtype, score, src, group_codes)


def relation_record(
    word_id: int,
    related_id: int,
    relation_type: str,
    score: Optional[float] = None,
    source: Optional[str] = None,
    group_codes: Optional[str] = None,
) -> Optional[RelationRecord]:
    row = normalize_relation_tuple(word_id, related_id, relation_type, score, source, group_codes)
    if row is None:
        return None
    return RelationRecord(*row)


def coerce_relation_records(
    rows: Sequence[Union[RelationRecord, RelationTuple]],
) -> List[RelationRecord]:
    out: List[RelationRecord] = []
    for row in rows:
        if isinstance(row, RelationRecord):
            out.append(row)
        else:
            out.append(RelationRecord(*row))
    return out


def bulk_insert_word_relations(
    db: Session,
    rows: Sequence[Union[RelationRecord, RelationTuple]],
    *,
    commit: bool = True,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, int]:
    """Insert in chunks; each chunk is one transaction; conflicts are dropped."""
    records = coerce_relation_records(rows)
    if not records:
        return {"attempted": 0, "chunks": 0}

    bind = db.get_bind()
    if bind.dialect.name == "sqlite":
        stmt = text(
            "INSERT OR IGNORE INTO word_relations "
            "(word_id, related_id, relation_type, score, source, group_codes) "
            "VALUES (:w, :r, :t, :s, :src, :gc)"
        )
    else:
        stmt = text(
            "INSERT INTO word_relations "
            "(word_id, related_id, relation_type, score, source, group_codes) "
            "VALUES (:w, :r, :t, :s, :src, :gc) "
            "ON CONFLICT (word_id, related_id, relation_type) DO NOTHING"
        )

    chunks = 0
    for i in range(0, len(records), chunk_size):
        params = [r.to_param() for r in records[i : i + chunk_size]]
        db.execute(stmt, params)
        chunks += 1
        if commit:
            db.commit()

    return {"attempted": len(records), "chunks": chunks}


def collect_unique_relation_tuples(edges: Iterable[RelationTuple]) -> List[RelationTuple]:
    """In-memory dedupe on (word_id, related_id, relation_type)."""
    seen: set[tuple[int, int, str]] = set()
    out: List[RelationTuple] = []
    for row in edges:
        w, r, t = row[0], row[1], row[2]
        key = (w, r, t)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


# ponytail: legacy name
BULK_BATCH = CHUNK_SIZE

__all__ = [
    "BULK_BATCH",
    "CHUNK_SIZE",
    "RelationRecord",
    "RelationTuple",
    "bulk_insert_word_relations",
    "coerce_relation_records",
    "collect_unique_relation_tuples",
    "normalize_relation_tuple",
    "relation_record",
]
