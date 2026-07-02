"""關係直寫 — 委派至 word_relations_build（canonical 三元組 + bulk insert）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relations
from app.models.word import WordRelation
from ingest.word_relations_build import build_word_relations, collect_guotong_flat_edges

ROOT = Path(__file__).resolve().parents[1]
FLAT_CHUNK = 5000


def ingest_flat_char_edges(
    db: Session,
    edges: Iterable[dict],
    *,
    char_to_id: Dict[str, int],
    chunk_size: int = FLAT_CHUNK,
    dedupe_existing: bool = False,
) -> dict:
    """Legacy batch path for tests; prefer build_word_relations for full rebuilds."""
    stats = {"candidates": 0, "inserted": 0, "skipped_no_id": 0, "skipped_existing": 0}
    batch: List[WordRelation] = []
    for e in edges:
        head_id = char_to_id.get(e["head"])
        tail_id = char_to_id.get(e["tail"])
        if head_id is None or tail_id is None:
            stats["skipped_no_id"] += 1
            continue
        w, r = canonical_word_ids(head_id, tail_id)
        if w == r:
            continue
        batch.append(WordRelation(
            word_id=w,
            related_id=r,
            relation_type=e["relation_type"],
            score=float(e.get("confidence") or 0.5),
            source=str(e.get("source") or "unknown")[:32],
        ))
        stats["candidates"] += 1
        if len(batch) >= chunk_size:
            stats["inserted"] += _flush_flat_batch(db, batch, dedupe_existing=dedupe_existing, stats=stats)
            batch.clear()
    if batch:
        stats["inserted"] += _flush_flat_batch(db, batch, dedupe_existing=dedupe_existing, stats=stats)
    return stats


def _dedupe_relation_batch(batch: List[WordRelation]) -> List[WordRelation]:
    seen: set[tuple[int, int, str]] = set()
    out: List[WordRelation] = []
    for r in batch:
        k = (int(r.word_id), int(r.related_id), str(r.relation_type))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _flush_flat_batch(
    db: Session,
    batch: List[WordRelation],
    *,
    dedupe_existing: bool,
    stats: dict,
) -> int:
    candidates = _dedupe_relation_batch(batch)
    stats["skipped_in_batch"] = stats.get("skipped_in_batch", 0) + len(batch) - len(candidates)
    _ = dedupe_existing  # ponytail: no-op; INSERT OR IGNORE replaces pre-fetch dedupe
    if not candidates:
        return 0
    return insert_relations(db, candidates)


def ingest_cilin_and_flat_static(
    db: Session,
    *,
    cilin_path: Path | None,
    flat_edges: List[dict],
    chunk_size: int = 300,
) -> dict:
    """Legacy chunked path for unit tests."""
    from ingest.syn_ant_build import ingest_cilin_leaf_direct

    stats: dict[str, Any] = {"cilin": {}, "flat": {}}
    if cilin_path is not None and cilin_path.is_file():
        stats["cilin"] = ingest_cilin_leaf_direct(
            db,
            cilin_path,
            source="cilin",
            chunk_size=chunk_size,
            dedupe_existing=True,
        )
    char_to_id = get_char_to_primary_id(db)
    stats["flat"] = ingest_flat_char_edges(
        db,
        flat_edges,
        char_to_id=char_to_id,
        dedupe_existing=True,
    )
    return stats


def ingest_static_relations(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    chunk_size: int = 300,
) -> dict:
    del chunk_size  # ponytail: unused; kept for CLI compat
    return build_word_relations(db, manifest_path=manifest_path, replace_static=True)


__all__ = [
    "collect_guotong_flat_edges",
    "ingest_cilin_and_flat_static",
    "ingest_flat_char_edges",
    "ingest_static_relations",
]
