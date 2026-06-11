from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import bindparam, text, tuple_

from ingest.cilin_leaf import groups_to_word_id_pairs, parse_leaf_groups
from ingest.relation_canonical import (
    canonical_relation_dict,
    canonical_word_ids,
)
from app.database import IS_POSTGRES
from app.models.word import Word, WordRelation, SynAntEdge

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


def get_db_char_set(db: Session) -> Set[str]:
    rows = db.query(Word.char).distinct().all()
    return {r[0] for r in rows if r[0]}


def get_char_to_ids(db: Session) -> Dict[str, List[int]]:
    mapping: Dict[str, List[int]] = {}
    for wid, ch in db.query(Word.id, Word.char).all():
        if not ch:
            continue
        mapping.setdefault(ch, []).append(int(wid))
    return mapping


def persist_staging_edges(
    db: Session,
    edges: Iterable[dict],
    *,
    clear: bool = True,
    clear_source: Optional[str] = None,
    batch_size: int = INSERT_BATCH,
) -> int:
    if clear:
        db.query(SynAntEdge).delete()
        db.commit()
    elif clear_source:
        db.query(SynAntEdge).filter(SynAntEdge.source == clear_source).delete()
        db.commit()
    count = 0
    batch: list[SynAntEdge] = []
    for e in edges:
        batch.append(SynAntEdge(
            head_char=e["head"],
            tail_char=e["tail"],
            relation_type=e["relation_type"],
            source=e.get("source"),
            confidence=e.get("confidence"),
            source_rank=e.get("source_rank"),
            evidence=json.dumps(e.get("evidence") or {}, ensure_ascii=False),
            license_tag=e.get("license_tag"),
            in_db_head=bool(e.get("in_db_head")),
            in_db_tail=bool(e.get("in_db_tail")),
        ))
        if len(batch) >= batch_size:
            db.add_all(batch)
            db.commit()
            count += len(batch)
            batch.clear()
    if batch:
        db.add_all(batch)
        db.commit()
        count += len(batch)
    return count


def _fetch_existing_keys(db: Session, keys: List[Tuple]) -> Set[Tuple]:
    existing: Set[Tuple] = set()
    for i in range(0, len(keys), SQL_IN_BATCH):
        chunk = keys[i:i + SQL_IN_BATCH]
        rows = (
            db.query(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type)
            .filter(tuple_(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type).in_(chunk))
            .all()
        )
        existing.update(rows)
    return existing


def _insert_relations(db: Session, relations: List[WordRelation]) -> int:
    inserted = 0
    for i in range(0, len(relations), INSERT_BATCH):
        batch: list[WordRelation] = []
        for r in relations[i:i + INSERT_BATCH]:
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


def get_char_to_primary_id(db: Session) -> Dict[str, int]:
    """One primary word id per char (minimum id) for relation ingest."""
    mapping = get_char_to_ids(db)
    return {ch: min(ids) for ch, ids in mapping.items() if ids}


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


def _build_cilin_syn_adjacency(db: Session, *, cilin_syn_source: str = "cilin") -> Dict[int, Set[int]]:
    """Bidirectional Cilin synonym neighbors keyed by word id."""
    syn_neighbors: Dict[int, Set[int]] = {}
    rows = (
        db.query(WordRelation.word_id, WordRelation.related_id)
        .filter(
            WordRelation.relation_type == "syn",
            WordRelation.source == cilin_syn_source,
        )
        .all()
    )
    for w, r in rows:
        syn_neighbors.setdefault(int(w), set()).add(int(r))
        syn_neighbors.setdefault(int(r), set()).add(int(w))
    return syn_neighbors


def expand_antonyms_via_cilin_synonyms(
    db: Session,
    *,
    source: str = "ant_cilin_exanded",
    cilin_syn_source: str = "cilin",
    confidence: float = 0.75,
    dedupe_existing: bool = True,
    batch_size: int = INSERT_BATCH,
) -> dict:
    """Expand ant relations using Cilin synonym neighbors of each antonym endpoint.

    Example: if 快樂 ant 悲傷 and 悲傷 syn 傷心/難過 (cilin), insert 快樂 ant 傷心/難過.
    Processes all existing ant seeds; dedupes by canonical (word_id, related_id, ant).
    """
    source = (source or "ant_cilin_exanded")[:32]
    stats = {
        "ant_seeds": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_self": 0,
        "skipped_no_syn": 0,
    }

    syn_neighbors = _build_cilin_syn_adjacency(db, cilin_syn_source=cilin_syn_source)
    if not syn_neighbors:
        return stats

    ant_rows = (
        db.query(WordRelation.word_id, WordRelation.related_id)
        .filter(WordRelation.relation_type == "ant")
        .all()
    )
    stats["ant_seeds"] = len(ant_rows)
    if not ant_rows:
        return stats

    candidates: Dict[Tuple[int, int, str], dict] = {}
    for word_id, related_id in ant_rows:
        a, b = int(word_id), int(related_id)
        syns_b = syn_neighbors.get(b)
        syns_a = syn_neighbors.get(a)
        if not syns_b and not syns_a:
            stats["skipped_no_syn"] += 1
            continue
        if syns_b:
            for syn_id in syns_b:
                if syn_id == a:
                    stats["skipped_self"] += 1
                    continue
                w, r = canonical_word_ids(a, syn_id)
                if w == r:
                    stats["skipped_self"] += 1
                    continue
                key = (w, r, "ant")
                candidates[key] = {
                    "word_id": w,
                    "related_id": r,
                    "relation_type": "ant",
                    "score": confidence,
                    "source": source,
                }
        if syns_a:
            for syn_id in syns_a:
                if syn_id == b:
                    stats["skipped_self"] += 1
                    continue
                w, r = canonical_word_ids(syn_id, b)
                if w == r:
                    stats["skipped_self"] += 1
                    continue
                key = (w, r, "ant")
                candidates[key] = {
                    "word_id": w,
                    "related_id": r,
                    "relation_type": "ant",
                    "score": confidence,
                    "source": source,
                }

    stats["candidate_pairs"] = len(candidates)
    if not candidates:
        return stats

    pending = list(candidates.values())
    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing: Set[Tuple] = set()
        for i in range(0, len(keys), SQL_IN_BATCH):
            existing.update(_fetch_existing_keys(db, keys[i:i + SQL_IN_BATCH]))
        before = len(pending)
        pending = [
            c for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        stats["skipped_existing"] = before - len(pending)

    if pending:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i:i + batch_size]
            stats["inserted"] += _insert_relations(db, [WordRelation(**c) for c in chunk])

    return stats


ANT_SYN_MIRROR_SOURCE = "ant_syn_mirror"


def _build_char_syn_adjacency(
    db: Session,
    *,
    include_static: bool = True,
) -> Dict[str, Set[str]]:
    """Bidirectional synonym neighbors keyed by char (word_relations syn + optional static)."""
    from sqlalchemy.orm import aliased

    adj: Dict[str, Set[str]] = {}
    w1 = aliased(Word)
    w2 = aliased(Word)
    for a, b in (
        db.query(w1.char, w2.char)
        .join(WordRelation, WordRelation.word_id == w1.id)
        .join(w2, WordRelation.related_id == w2.id)
        .filter(WordRelation.relation_type == "syn")
        .all()
    ):
        if not a or not b or a == b:
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    if include_static:
        try:
            from utils import ensure_thesaurus_loaded, get_synonyms

            ensure_thesaurus_loaded()
            db_chars = get_db_char_set(db)
            for ch in db_chars:
                for syn in get_synonyms(ch):
                    if not syn or syn == ch or syn not in db_chars:
                        continue
                    adj.setdefault(ch, set()).add(syn)
                    adj.setdefault(syn, set()).add(ch)
        except Exception:
            pass

    return adj


def _collect_direct_ant_oriented_pairs(
    db: Session,
    *,
    exclude_sources: Optional[Set[str]] = None,
) -> Set[Tuple[str, str]]:
    """(head_char, ant_endpoint_char) for each non-mirror ant relation, both orientations."""
    from sqlalchemy.orm import aliased

    exclude_sources = exclude_sources or set()
    w1 = aliased(Word)
    w2 = aliased(Word)
    q = (
        db.query(w1.char, w2.char, WordRelation.source)
        .join(WordRelation, WordRelation.word_id == w1.id)
        .join(w2, WordRelation.related_id == w2.id)
        .filter(WordRelation.relation_type == "ant")
    )
    oriented: Set[Tuple[str, str]] = set()
    for a, b, src in q.all():
        if not a or not b or a == b:
            continue
        if src in exclude_sources:
            continue
        oriented.add((a, b))
        oriented.add((b, a))
    return oriented


def collect_ant_mirror_char_pairs(
    db: Session,
    *,
    include_static: bool = True,
    exclude_sources: Optional[Set[str]] = None,
) -> Set[Tuple[str, str]]:
    """Char pairs (head, tail) matching runtime ``!head`` expansion: ant endpoints + their syns.

    Example: if 開心 ant 悲傷 and 悲傷 syn 傷心, yields (開心, 悲傷) and (開心, 傷心).
    Conceptually ``!開心`` mirrors ``~悲傷`` for the expanded portion.
    """
    exclude_sources = exclude_sources or {ANT_SYN_MIRROR_SOURCE}
    syn_adj = _build_char_syn_adjacency(db, include_static=include_static)
    seeds = _collect_direct_ant_oriented_pairs(db, exclude_sources=exclude_sources)
    pairs: Set[Tuple[str, str]] = set()
    for head, endpoint in seeds:
        if head == endpoint:
            continue
        pairs.add((head, endpoint))
        for syn_char in syn_adj.get(endpoint, set()):
            if syn_char and syn_char != head:
                pairs.add((head, syn_char))
    return pairs


def expand_antonyms_via_syn_endpoints(
    db: Session,
    *,
    source: str = ANT_SYN_MIRROR_SOURCE,
    confidence: float = 0.72,
    dedupe_existing: bool = True,
    include_static: bool = True,
    batch_size: int = INSERT_BATCH,
) -> dict:
    """Persist ``!query`` results as ant word_relations via ant-endpoint synonym expansion.

    Uses direct ant seeds (excluding prior mirror rows), then adds one hop through
    synonym neighbors of each ant endpoint — same logic as runtime ``!`` search.
    """
    source = (source or ANT_SYN_MIRROR_SOURCE)[:32]
    stats = {
        "ant_seed_orientations": 0,
        "mirror_char_pairs": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_no_char_id": 0,
        "skipped_self": 0,
    }

    char_to_id = get_char_to_primary_id(db)
    seeds = _collect_direct_ant_oriented_pairs(db, exclude_sources={source})
    stats["ant_seed_orientations"] = len(seeds)
    if not seeds:
        return stats

    mirror_pairs = collect_ant_mirror_char_pairs(
        db,
        include_static=include_static,
        exclude_sources={source},
    )
    stats["mirror_char_pairs"] = len(mirror_pairs)

    candidates: Dict[Tuple[int, int, str], dict] = {}
    for head_char, tail_char in mirror_pairs:
        if head_char == tail_char:
            stats["skipped_self"] += 1
            continue
        head_id = char_to_id.get(head_char)
        tail_id = char_to_id.get(tail_char)
        if not head_id or not tail_id:
            stats["skipped_no_char_id"] += 1
            continue
        w, r = canonical_word_ids(head_id, tail_id)
        if w == r:
            stats["skipped_self"] += 1
            continue
        key = (w, r, "ant")
        candidates[key] = {
            "word_id": w,
            "related_id": r,
            "relation_type": "ant",
            "score": confidence,
            "source": source,
        }

    stats["candidate_pairs"] = len(candidates)
    if not candidates:
        return stats

    pending = list(candidates.values())
    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing: Set[Tuple] = set()
        for i in range(0, len(keys), SQL_IN_BATCH):
            existing.update(_fetch_existing_keys(db, keys[i:i + SQL_IN_BATCH]))
        before = len(pending)
        pending = [
            c for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        stats["skipped_existing"] = before - len(pending)

    if pending:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i:i + batch_size]
            stats["inserted"] += _insert_relations(db, [WordRelation(**c) for c in chunk])

    return stats


def staging_report(db: Session) -> str:
    total = db.query(SynAntEdge).count()
    by_source: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for src, rtype in db.query(SynAntEdge.source, SynAntEdge.relation_type).all():
        by_source[src or "unknown"] = by_source.get(src or "unknown", 0) + 1
        by_type[rtype or "unknown"] = by_type.get(rtype or "unknown", 0) + 1

    lines = [f"Staging edges: {total}"]
    for k, v in sorted(by_type.items()):
        lines.append(f"  type {k}: {v}")
    for k, v in sorted(by_source.items(), key=lambda x: -x[1])[:20]:
        lines.append(f"  source {k}: {v}")
    return "\n".join(lines)
