from __future__ import annotations

from typing import Dict, List, Set, Tuple

from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_relation_dict
from app.models.word import WordRelation

SQL_IN_BATCH = 300
INSERT_BATCH = 300


def fetch_existing_relation_keys(db: Session, keys: List[Tuple]) -> Set[Tuple]:
    existing: Set[Tuple] = set()
    for i in range(0, len(keys), SQL_IN_BATCH):
        chunk = keys[i : i + SQL_IN_BATCH]
        rows = (
            db.query(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type)
            .filter(tuple_(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type).in_(chunk))
            .all()
        )
        existing.update(rows)
    return existing


def insert_relations(db: Session, relations: List[WordRelation]) -> int:
    inserted = 0
    for i in range(0, len(relations), INSERT_BATCH):
        batch: list[WordRelation] = []
        for r in relations[i : i + INSERT_BATCH]:
            if isinstance(r, WordRelation):
                d = {
                    "word_id": r.word_id,
                    "related_id": r.related_id,
                    "relation_type": r.relation_type,
                    "score": r.score,
                    "source": r.source,
                    "group_codes": r.group_codes,
                }
                if r.id is not None:
                    d["id"] = r.id
                batch.append(WordRelation(**canonical_relation_dict(d)))
            else:
                batch.append(WordRelation(**canonical_relation_dict(r)))
        db.add_all(batch)
        db.commit()
        inserted += len(batch)
    return inserted


def insert_relation_candidates(
    db: Session,
    candidates: Dict[Tuple[int, int, str], dict],
    *,
    dedupe_existing: bool,
    batch_size: int,
) -> Tuple[int, int]:
    if not candidates:
        return 0, 0
    pending = list(candidates.values())
    skipped_existing = 0
    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing: Set[Tuple] = set()
        for i in range(0, len(keys), SQL_IN_BATCH):
            existing.update(fetch_existing_relation_keys(db, keys[i : i + SQL_IN_BATCH]))
        before = len(pending)
        pending = [
            c
            for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        skipped_existing = before - len(pending)
    inserted = 0
    if pending:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i : i + batch_size]
            inserted += insert_relations(db, [WordRelation(**c) for c in chunk])
    return inserted, skipped_existing
