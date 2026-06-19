"""syn_ant_edges → word_relations build + cilin direct ingest（CONTEXT § 關係寫入 adapter）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.database import IS_POSTGRES
from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_ids, get_char_to_primary_id
from app.domain.relations.store import (
    fetch_existing_relation_keys as _fetch_existing_keys,
    insert_relations as _insert_relations,
)
from app.models.word import Word, WordRelation, SynAntEdge
from ingest.cilin_leaf import groups_to_word_id_pairs, parse_leaf_groups

STAGING_BATCH = 300
SQL_IN_BATCH = 300
INSERT_BATCH = 300

def _group_codes_from_staging_evidence(evidence_raw: Optional[str]) -> Optional[str]:
    """Extract group_codes JSON from staging evidence, or derive from leaf group code."""
    from ingest.cilin_leaf import hierarchy_codes_json

    if not evidence_raw:
        return None
    try:
        data = json.loads(evidence_raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    codes = data.get("group_codes")
    if isinstance(codes, list) and codes:
        return json.dumps(codes, ensure_ascii=False)
    leaf = data.get("group")
    if isinstance(leaf, str) and leaf:
        return hierarchy_codes_json(leaf)
    return None


def _build_relations_sql_bulk(
    db: Session,
    *,
    allow_external: bool,
    source: Optional[str] = None,
    staging_ids: Optional[List[int]] = None,
) -> int:
    """Insert relations for all or selected staging rows. Returns rows inserted."""
    if not allow_external:
        edge_filter = "e.in_db_head = 1 AND e.in_db_tail = 1"
    else:
        edge_filter = "1=1"

    extra = []
    params: dict = {}
    if source:
        extra.append("e.source = :source")
        params["source"] = source
    if staging_ids:
        extra.append("e.id IN :ids")
        params["ids"] = list(staging_ids)
    if extra:
        edge_filter = f"{edge_filter} AND " + " AND ".join(extra)

    if IS_POSTGRES:
        sql = text(f"""
            INSERT INTO word_relations (word_id, related_id, relation_type, score, source, group_codes)
            SELECT DISTINCT
                CASE WHEN w1.id < w2.id THEN w1.id ELSE w2.id END,
                CASE WHEN w1.id < w2.id THEN w2.id ELSE w1.id END,
                e.relation_type, e.confidence, LEFT(e.source, 32),
                (e.evidence::json->'group_codes')::text
            FROM syn_ant_edges e
            INNER JOIN words w1 ON w1.char = e.head_char
            INNER JOIN words w2 ON w2.char = e.tail_char
            WHERE {edge_filter} AND w1.id <> w2.id
            ON CONFLICT (word_id, related_id, relation_type) DO NOTHING
        """)
    else:
        sql = text(f"""
            INSERT OR IGNORE INTO word_relations (word_id, related_id, relation_type, score, source, group_codes)
            SELECT DISTINCT
                CASE WHEN w1.id < w2.id THEN w1.id ELSE w2.id END,
                CASE WHEN w1.id < w2.id THEN w2.id ELSE w1.id END,
                e.relation_type, e.confidence, substr(e.source, 1, 32),
                json_extract(e.evidence, '$.group_codes')
            FROM syn_ant_edges e
            INNER JOIN words w1 ON w1.char = e.head_char
            INNER JOIN words w2 ON w2.char = e.tail_char
            WHERE {edge_filter} AND w1.id <> w2.id
        """)

    if staging_ids:
        sql = sql.bindparams(bindparam("ids", expanding=True))

    result = db.execute(sql, params)
    db.commit()
    return result.rowcount if result.rowcount is not None and result.rowcount >= 0 else 0


def build_word_relations_from_staging(
    db: Session,
    *,
    allow_external: bool = False,
    char_to_ids: Optional[Dict[str, List[int]]] = None,
    batch_size: int = STAGING_BATCH,
    source: Optional[str] = None,
    use_batched_sql: bool = False,
) -> dict:
    """Merge syn_ant_edges into word_relations."""
    total_staging = db.query(SynAntEdge).count()
    if source:
        total_staging = db.query(SynAntEdge).filter(SynAntEdge.source == source).count()

    stats = {
        "staging": total_staging,
        "inserted": 0,
        "skipped_no_id": 0,
        "skipped_external": 0,
        "method": "sql_bulk",
        "batches": 0,
    }

    if total_staging == 0:
        return stats

    if use_batched_sql or batch_size < total_staging:
        stats["method"] = "sql_batched"
        last_id = 0
        q = db.query(SynAntEdge.id).order_by(SynAntEdge.id)
        if source:
            q = db.query(SynAntEdge.id).filter(SynAntEdge.source == source).order_by(SynAntEdge.id)
        while True:
            ids = [
                row[0]
                for row in q.filter(SynAntEdge.id > last_id).limit(batch_size).all()
            ]
            if not ids:
                break
            last_id = ids[-1]
            stats["inserted"] += _build_relations_sql_bulk(
                db,
                allow_external=allow_external,
                source=None,
                staging_ids=ids,
            )
            stats["batches"] += 1
            if stats["batches"] % 50 == 0:
                print(f"  build-relations batch {stats['batches']}: inserted so far {stats['inserted']}", flush=True)
        return stats

    try:
        stats["inserted"] = _build_relations_sql_bulk(db, allow_external=allow_external, source=source)
        if not allow_external and source is None:
            stats["skipped_external"] = (
                db.query(SynAntEdge)
                .filter((SynAntEdge.in_db_head == 0) | (SynAntEdge.in_db_tail == 0))
                .count()
            )
        return stats
    except Exception as exc:
        print(f"[merge] SQL bulk path failed ({type(exc).__name__}: {exc}), falling back to batched ORM")

    char_to_ids = char_to_ids or get_char_to_ids(db)
    total_staging = db.query(SynAntEdge).count()
    stats = {
        "staging": total_staging,
        "inserted": 0,
        "skipped_no_id": 0,
        "skipped_external": 0,
        "method": "orm_batch",
    }

    seen: Set[Tuple] = set()
    last_id = 0
    while True:
        rows = (
            db.query(SynAntEdge)
            .filter(SynAntEdge.id > last_id)
            .order_by(SynAntEdge.id)
            .limit(STAGING_BATCH)
            .all()
        )
        if not rows:
            break
        last_id = rows[-1].id

        pending: Dict[Tuple, dict] = {}
        for row in rows:
            if not allow_external and not (row.in_db_head and row.in_db_tail):
                stats["skipped_external"] += 1
                continue
            head_ids = char_to_ids.get(row.head_char) or []
            tail_ids = char_to_ids.get(row.tail_char) or []
            if not head_ids or not tail_ids:
                stats["skipped_no_id"] += 1
                continue
            for wid in head_ids:
                for rid in tail_ids:
                    if wid == rid:
                        continue
                    w, r = canonical_word_ids(wid, rid)
                    pair_key = (w, r, row.relation_type)
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)
                    pending[pair_key] = {
                        "word_id": w,
                        "related_id": r,
                        "relation_type": row.relation_type,
                        "score": row.confidence,
                        "source": (row.source or "")[:32],
                        "group_codes": _group_codes_from_staging_evidence(row.evidence),
                    }

        if not pending:
            continue

        keys = list(pending.keys())
        existing = _fetch_existing_keys(db, keys)
        to_insert = [WordRelation(**pending[k]) for k in pending if k not in existing]
        stats["inserted"] += _insert_relations(db, to_insert)

    return stats


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

        for code, words in groups:
            in_db = sum(1 for w in words if w in char_to_id)
            if in_db < 2:
                stats["skipped_no_id"] += max(0, len(words) - in_db)

        candidates = groups_to_word_id_pairs(groups, char_to_id)
        for c in candidates:
            c["source"] = source[:32]
            c["score"] = confidence
        stats["candidate_pairs"] += len(candidates)

        if not candidates:
            continue

        if dedupe_existing:
            keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in candidates]
            existing = _fetch_existing_keys(db, keys)
            candidates = [c for c in candidates if (c["word_id"], c["related_id"], c["relation_type"]) not in existing]
            stats["skipped_existing"] += len(keys) - len(candidates)

        if candidates:
            stats["inserted"] += _insert_relations(db, [WordRelation(**c) for c in candidates])

        if stats["batches"] % 20 == 0:
            print(
                f"  direct batch {stats['batches']}: groups={stats['groups']} "
                f"inserted={stats['inserted']} skipped_existing={stats['skipped_existing']}",
                flush=True,
            )

    return stats


def clear_word_relations_source(db: Session, source: str) -> int:
    n = db.query(WordRelation).filter(WordRelation.source == source).delete()
    db.commit()
    return n

__all__ = [
    "build_word_relations_from_staging",
    "clear_word_relations_source",
    "ingest_cilin_leaf_direct",
]
