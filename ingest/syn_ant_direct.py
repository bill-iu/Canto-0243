"""關係直寫 — cilin leaf + 扁平靜態邊直寫 word_relations（CONTEXT § 關係直寫）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import (
    fetch_existing_relation_keys,
    insert_relations,
)
from app.domain.thesaurus.port import StaticThesaurusPort
from app.models.word import WordRelation
from app.repositories.word_relation_repo import load_db_char_set
from ingest.syn_ant_build import clear_word_relations_source, ingest_cilin_leaf_direct
from ingest.syn_ant_manifest import load_manifest, select_sources
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "syn_ant" / "sources.yaml"
FLAT_CHUNK = 5000
STATIC_RELATION_SOURCES = ("cilin", "guotong", "antisem")


def collect_guotong_antisem_edges(port: StaticThesaurusPort, *, source_rank: int) -> List[dict]:
    edges: List[dict] = []
    for head in port.iter_literal_heads():
        for tail in port.get_guotong_synonyms(head):
            edges.append({
                "head": head,
                "tail": tail,
                "relation_type": "syn",
                "source": "guotong",
                "confidence": 0.8,
                "source_rank": source_rank,
            })
        for tail in port.get_antonyms(head):
            edges.append({
                "head": head,
                "tail": tail,
                "relation_type": "ant",
                "source": "antisem",
                "confidence": 0.85,
                "source_rank": source_rank,
            })
    return edges


def ingest_flat_char_edges(
    db: Session,
    edges: Iterable[dict],
    *,
    char_to_id: Dict[str, int],
    chunk_size: int = FLAT_CHUNK,
    dedupe_existing: bool = False,
) -> dict:
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


def _flush_flat_batch(
    db: Session,
    batch: List[WordRelation],
    *,
    dedupe_existing: bool,
    stats: dict,
) -> int:
    candidates = batch
    if dedupe_existing:
        keys = [(r.word_id, r.related_id, r.relation_type) for r in candidates]
        existing = fetch_existing_relation_keys(db, keys)
        before = len(candidates)
        candidates = [r for r in candidates if (r.word_id, r.related_id, r.relation_type) not in existing]
        stats["skipped_existing"] += before - len(candidates)
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
    stats: dict[str, Any] = {"cilin": {}, "flat": {}}
    if cilin_path is not None and cilin_path.is_file():
        stats["cilin"] = ingest_cilin_leaf_direct(
            db,
            cilin_path,
            source="cilin",
            chunk_size=chunk_size,
            dedupe_existing=False,
        )
    char_to_id = get_char_to_primary_id(db)
    stats["flat"] = ingest_flat_char_edges(
        db,
        flat_edges,
        char_to_id=char_to_id,
        dedupe_existing=False,
    )
    return stats


def ingest_static_relations(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    chunk_size: int = 300,
) -> dict:
    manifest = load_manifest(manifest_path or DEFAULT_MANIFEST)
    sources = select_sources(manifest, defaults_only=True)
    static_src = next((s for s in sources if s.get("parser") == "current_static"), None)
    if static_src is None:
        raise FileNotFoundError("current_static source not found in syn_ant manifest")

    paths = static_src.get("paths") or {}
    rank = int(static_src.get("source_rank") or 70)

    for source_id in STATIC_RELATION_SOURCES:
        clear_word_relations_source(db, source_id)

    cilin_rel = paths.get("cilin")
    cilin_path = (ROOT / cilin_rel) if cilin_rel else None
    if cilin_path is not None and not cilin_path.is_file():
        cilin_path = None

    port = StaticThesaurusPort(
        antisem_path=str(ROOT / paths["antisem"]) if paths.get("antisem") else None,
        thesaurus_syn_path=str(ROOT / paths["thesaurus_syn"]) if paths.get("thesaurus_syn") else None,
        thesaurus_ant_path=str(ROOT / paths["thesaurus_ant"]) if paths.get("thesaurus_ant") else None,
        auto_load=True,
    )
    raw_flat = collect_guotong_antisem_edges(port, source_rank=rank)
    db_chars = load_db_char_set(db)
    flat_edges = merge_staging_edges(
        normalize_edges(raw_flat, db_chars=db_chars, allow_external=False)
    )

    return ingest_cilin_and_flat_static(
        db,
        cilin_path=cilin_path,
        flat_edges=flat_edges,
        chunk_size=chunk_size,
    )


__all__ = [
    "collect_guotong_antisem_edges",
    "ingest_cilin_and_flat_static",
    "ingest_flat_char_edges",
    "ingest_static_relations",
]
