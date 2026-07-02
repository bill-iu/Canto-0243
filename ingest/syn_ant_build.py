"""Cilin + flat char edges → word_relations（CONTEXT § 關係寫入 adapter）。"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relations
from ingest.cilin_leaf import groups_to_word_id_pairs, parse_leaf_groups

INSERT_BATCH = 300


def ingest_cilin_leaf_direct(
    db: Session,
    path: Path,
    *,
    source: str = "cilin",
    chunk_size: int = 300,
    confidence: float = 0.85,
    dedupe_existing: bool = True,
) -> dict:
    """Ingest leaf Cilin groups directly into word_relations with canonical dedupe."""
    _ = dedupe_existing  # ponytail: no-op; INSERT OR IGNORE replaces pre-fetch dedupe
    from ingest.cilin_leaf import iter_cilin_leaf_line_chunks

    char_to_id = get_char_to_primary_id(db)
    stats = {
        "method": "direct",
        "groups": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_no_id": 0,
        "batches": 0,
    }

    for lines in iter_cilin_leaf_line_chunks(path, chunk_size=chunk_size):
        stats["batches"] += 1
        groups = parse_leaf_groups(lines)
        stats["groups"] += len(groups)

        for _code, words in groups:
            in_db = sum(1 for w in words if w in char_to_id)
            if in_db < 2:
                stats["skipped_no_id"] += max(0, len(words) - in_db)

        candidates = groups_to_word_id_pairs(groups, char_to_id)
        for c in candidates:
            c["source"] = source[:32]
            c["score"] = confidence
        stats["candidate_pairs"] += len(candidates)

        if candidates:
            from app.models.word import WordRelation

            stats["inserted"] += insert_relations(
                db, [WordRelation(**c) for c in candidates]
            )

        if stats["batches"] % 20 == 0:
            print(
                f"  cilin direct batch {stats['batches']}: groups={stats['groups']} "
                f"inserted={stats['inserted']} skipped_existing={stats['skipped_existing']}",
                flush=True,
            )

    return stats


def clear_word_relations_source(db: Session, source: str) -> int:
    from app.models.word import WordRelation

    n = db.query(WordRelation).filter(WordRelation.source == source).delete()
    db.commit()
    return n


__all__ = [
    "clear_word_relations_source",
    "ingest_cilin_leaf_direct",
]
