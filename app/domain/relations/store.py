from __future__ import annotations

from typing import Dict, List, Sequence, Tuple, Union

from sqlalchemy.orm import Session

from app.domain.relations.bulk_insert import (
    CHUNK_SIZE,
    RelationRecord,
    RelationTuple,
    bulk_insert_word_relations,
    relation_record,
)
from app.models.word import WordRelation

# ponytail: legacy alias for ingest CLI defaults
INSERT_BATCH = CHUNK_SIZE


def _records_from_rows(relations: Sequence[Union[WordRelation, dict]]) -> List[RelationRecord]:
    out: List[RelationRecord] = []
    for row in relations:
        if isinstance(row, WordRelation):
            rec = relation_record(
                int(row.word_id),
                int(row.related_id),
                str(row.relation_type),
                row.score,
                row.source,
                row.group_codes,
            )
        else:
            rec = relation_record(
                row["word_id"],
                row["related_id"],
                row["relation_type"],
                row.get("score"),
                row.get("source"),
                row.get("group_codes"),
            )
        if rec is not None:
            out.append(rec)
    return out


def insert_relations(
    db: Session,
    relations: List[WordRelation],
    *,
    commit: bool = True,
    chunk_size: int = CHUNK_SIZE,
) -> int:
    records = _records_from_rows(relations)
    if not records:
        return 0
    stats = bulk_insert_word_relations(db, records, commit=commit, chunk_size=chunk_size)
    return stats["attempted"]


def insert_relation_records(
    db: Session,
    rows: Sequence[Union[RelationRecord, RelationTuple]],
    *,
    commit: bool = True,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, int]:
    return bulk_insert_word_relations(db, rows, commit=commit, chunk_size=chunk_size)


def insert_relation_candidates(
    db: Session,
    candidates: Dict[Tuple[int, int, str], dict],
    *,
    dedupe_existing: bool,
    batch_size: int,
    commit: bool = True,
) -> Tuple[int, int]:
    _ = dedupe_existing  # ponytail: no-op; INSERT OR IGNORE replaces pre-fetch dedupe
    if not candidates:
        return 0, 0
    records = _records_from_rows(list(candidates.values()))
    if not records:
        return 0, 0
    stats = bulk_insert_word_relations(
        db, records, commit=commit, chunk_size=batch_size or CHUNK_SIZE
    )
    return stats["attempted"], 0
