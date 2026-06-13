from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import bindparam, text, tuple_

from ingest.cilin_leaf import groups_to_word_id_pairs, parse_leaf_groups
from app.domain.relations.canonical import (
    canonical_relation_dict,
    canonical_word_ids,
)
from app.domain.relations.char_index import get_char_to_ids, get_char_to_primary_id
from app.domain.relations.store import (
    fetch_existing_relation_keys as _fetch_existing_keys,
    insert_relation_candidates as _insert_bridge_candidates,
    insert_relations as _insert_relations,
)
from app.repositories.word_relation_repo import load_db_char_set
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
            from app.thesaurus.static_index import ensure_thesaurus_loaded, get_synonyms

            ensure_thesaurus_loaded()
            db_chars = load_db_char_set(db)
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


ANT_SYN_BRIDGE_SOURCE = "ant_syn_bridge"


def _empty_bridge_stats() -> dict:
    return {
        "total_targets": 0,
        "offset": 0,
        "targets": 0,
        "batches": 0,
        "bridged": 0,
        "skipped_no_bridge": 0,
        "skipped_no_model": 0,
        "skipped_self": 0,
        "skipped_no_char_id": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
    }


def _merge_bridge_stats(into: dict, chunk: dict) -> None:
    for key, value in chunk.items():
        if key in ("total_targets", "offset", "batches", "targets"):
            continue
        if isinstance(value, (int, float)):
            into[key] = into.get(key, 0) + value


def _process_bridge_targets(
    db: Session,
    targets: List[str],
    *,
    source: str,
    include_static: bool,
    embed_batch_size: int,
    model,
    char_to_id: Dict[str, int],
    pool_ctx,
    global_ant_chars: Set[str],
    embedding_cache: Dict[str, List[float]],
    progress_interval: int = 50,
    on_progress=None,
    progress_base: int = 0,
) -> Tuple[dict, Dict[Tuple[int, int, str], dict]]:
    from app.utils.embedding import cosine_similarity

    stats = _empty_bridge_stats()
    stats["targets"] = len(targets)
    candidates: Dict[Tuple[int, int, str], dict] = {}

    def _cached_embeddings(chars: Iterable[str]) -> None:
        missing = [c for c in dict.fromkeys(chars) if c and c not in embedding_cache]
        for i in range(0, len(missing), embed_batch_size):
            chunk = missing[i : i + embed_batch_size]
            embedding_cache.update(_encode_char_batch(chunk, model))

    def _syn_might_have_ants(syn_char: str) -> bool:
        if syn_char in global_ant_chars:
            return True
        if include_static and pool_ctx.thesaurus.get_antonyms(syn_char):
            return True
        return False

    for idx, head_char in enumerate(targets):
        if progress_interval > 0 and on_progress is not None and idx > 0 and idx % progress_interval == 0:
            on_progress(progress_base + idx, stats)

        head_id = char_to_id.get(head_char)
        if not head_id:
            stats["skipped_no_char_id"] += 1
            continue

        syn_pool = pool_ctx.relation_chars(head_char, "syn")
        bridge_options: List[Tuple[str, List[str]]] = []
        chars_to_embed = [head_char, *syn_pool]
        for syn_char in syn_pool:
            if not syn_char or syn_char == head_char:
                continue
            if not _syn_might_have_ants(syn_char):
                continue
            direct_ants = pool_ctx.relation_chars(syn_char, "ant")
            if not direct_ants:
                continue
            chars_to_embed.extend(direct_ants)
            bridge_options.append((syn_char, direct_ants))

        if not bridge_options:
            stats["skipped_no_bridge"] += 1
            continue

        _cached_embeddings(chars_to_embed)
        head_vec = embedding_cache.get(head_char)
        if not head_vec:
            stats["skipped_no_bridge"] += 1
            continue

        best_syn = None
        best_score = -1.0
        best_ants: List[str] = []
        for syn_char, direct_ants in bridge_options:
            syn_vec = embedding_cache.get(syn_char)
            if not syn_vec:
                continue
            score = cosine_similarity(head_vec, syn_vec)
            if score > best_score or (score == best_score and (best_syn is None or syn_char < best_syn)):
                best_score = score
                best_syn = syn_char
                best_ants = direct_ants

        if not best_syn or not best_ants:
            stats["skipped_no_bridge"] += 1
            continue

        stats["bridged"] += 1
        bridge_score = round(float(best_score), 4)

        for ant_char in best_ants:
            if not ant_char or ant_char == head_char:
                stats["skipped_self"] += 1
                continue
            tail_id = char_to_id.get(ant_char)
            if not tail_id:
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
                "score": bridge_score,
                "source": source,
            }

    stats["candidate_pairs"] = len(candidates)
    return stats, candidates


def _chars_with_relations_of_type(db: Session, relation_type: str) -> Set[str]:
    from sqlalchemy.orm import aliased

    chars: Set[str] = set()
    w_head = aliased(Word)
    w_tail = aliased(Word)
    for ch, in (
        db.query(w_head.char)
        .join(WordRelation, WordRelation.word_id == w_head.id)
        .filter(WordRelation.relation_type == relation_type)
        .distinct()
        .all()
    ):
        if ch:
            chars.add(ch)
    for ch, in (
        db.query(w_tail.char)
        .join(WordRelation, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.relation_type == relation_type)
        .distinct()
        .all()
    ):
        if ch:
            chars.add(ch)
    return chars


def _encode_char_batch(chars: List[str], model) -> Dict[str, List[float]]:
    if not chars or model is None:
        return {}
    unique = list(dict.fromkeys(c for c in chars if c))
    embs = model.encode(unique, normalize_embeddings=True)
    return {ch: embs[i].tolist() for i, ch in enumerate(unique)}


def _load_embedding_model():
    from app.utils.embedding import enable_embedding_model_for_ingest

    enable_embedding_model_for_ingest()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def expand_antonyms_via_embedding_syn_bridge(
    db: Session,
    *,
    source: str = ANT_SYN_BRIDGE_SOURCE,
    dedupe_existing: bool = True,
    include_static: bool = True,
    batch_size: int = INSERT_BATCH,
    embed_batch_size: int = 256,
    offset: int = 0,
    limit: Optional[int] = None,
    chunk_size: Optional[int] = None,
    on_batch=None,
    on_progress=None,
    progress_interval: int = 50,
) -> dict:
    """近義橋反義：有 syn、無 ant 的字面 → embedding 挑橋接近義 → 借其 direct ant。

    See CONTEXT § 近義橋反義.

    When ``chunk_size`` is set, processes targets in chunks and inserts after each chunk
    (checkpoint-friendly). ``offset`` / ``limit`` slice the sorted target list.
    """
    from ingest.bridge_pool_context import IngestBridgePoolContext

    source = (source or ANT_SYN_BRIDGE_SOURCE)[:32]
    stats = _empty_bridge_stats()
    stats["offset"] = max(0, int(offset or 0))

    syn_chars = _chars_with_relations_of_type(db, "syn")
    ant_chars = _chars_with_relations_of_type(db, "ant")
    all_targets = sorted(syn_chars - ant_chars)
    stats["total_targets"] = len(all_targets)

    start = stats["offset"]
    end = len(all_targets) if limit is None else min(len(all_targets), start + max(0, int(limit)))
    targets = all_targets[start:end]
    stats["targets"] = len(targets)
    if not targets:
        return stats

    model = _load_embedding_model()
    if model is None:
        stats["skipped_no_model"] = len(targets)
        return stats

    char_to_id = get_char_to_primary_id(db)
    pool_ctx = IngestBridgePoolContext(db, include_static=include_static)
    global_ant_chars = ant_chars
    embedding_cache: Dict[str, List[float]] = {}

    chunk = max(0, int(chunk_size)) if chunk_size else 0
    if chunk > 0:
        total_batches = (len(targets) + chunk - 1) // chunk
        for batch_idx in range(total_batches):
            batch_start = batch_idx * chunk
            batch_targets = targets[batch_start : batch_start + chunk]
            chunk_stats, candidates = _process_bridge_targets(
                db,
                batch_targets,
                source=source,
                include_static=include_static,
                embed_batch_size=embed_batch_size,
                model=model,
                char_to_id=char_to_id,
                pool_ctx=pool_ctx,
                global_ant_chars=global_ant_chars,
                embedding_cache=embedding_cache,
                progress_interval=progress_interval,
                on_progress=on_progress,
                progress_base=start + batch_start,
            )
            inserted, skipped_existing = _insert_bridge_candidates(
                db,
                candidates,
                dedupe_existing=dedupe_existing,
                batch_size=batch_size,
            )
            chunk_stats["inserted"] = inserted
            chunk_stats["skipped_existing"] = skipped_existing
            embedding_cache.clear()
            stats["batches"] += 1
            _merge_bridge_stats(stats, chunk_stats)
            if on_batch is not None:
                chunk_stats["total_targets"] = stats["total_targets"]
                on_batch(
                    batch_idx + 1,
                    total_batches,
                    chunk_stats,
                    start + batch_start + len(batch_targets),
                )
        return stats

    chunk_stats, candidates = _process_bridge_targets(
        db,
        targets,
        source=source,
        include_static=include_static,
        embed_batch_size=embed_batch_size,
        model=model,
        char_to_id=char_to_id,
        pool_ctx=pool_ctx,
        global_ant_chars=global_ant_chars,
        embedding_cache=embedding_cache,
        progress_interval=progress_interval,
        on_progress=on_progress,
        progress_base=start,
    )
    inserted, skipped_existing = _insert_bridge_candidates(
        db,
        candidates,
        dedupe_existing=dedupe_existing,
        batch_size=batch_size,
    )
    chunk_stats["inserted"] = inserted
    chunk_stats["skipped_existing"] = skipped_existing
    stats["batches"] = 1
    _merge_bridge_stats(stats, chunk_stats)
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
