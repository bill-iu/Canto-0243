"""Precompute word_relations: canonical id pairs + single bulk insert (CONTEXT § 關係寫入)."""
from __future__ import annotations

import itertools
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.bulk_insert import RelationTuple, normalize_relation_tuple
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relation_records
from app.domain.thesaurus.port import StaticThesaurusPort
from app.lexicon.compound_antonyms import load_compound_antonyms
from app.models.word import Word
from ingest.cilin_leaf import hierarchy_codes_json, parse_leaf_groups
from ingest.compound_antonyms import _compound_exists
from ingest.syn_ant_build import clear_word_relations_source
from ingest.syn_ant_manifest import load_manifest, select_sources
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from app.repositories.word_relation_repo import load_db_char_set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "syn_ant" / "sources.yaml"
DEFAULT_COMPOUND_PATH = ROOT / "data" / "syn_ant" / "compound_antonyms.txt"
STATIC_SOURCES = ("cilin", "guotong", "compound_ant")
LEGACY_SOURCES = ("antisem",)

# ponytail: lower = wins when same (word_id, related_id, relation_type) from multiple static sources
_SOURCE_RANK = {"cilin": 10, "guotong": 20, "compound_ant": 30}


def collect_guotong_flat_edges(port: StaticThesaurusPort, *, source_rank: int) -> List[dict]:
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
                "source": "guotong",
                "confidence": 0.85,
                "source_rank": source_rank,
            })
    return edges


def _read_cilin_leaf_groups(path: Path) -> List[Tuple[str, List[str]]]:
    lines: List[str] = []
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            lines = path.read_text(encoding=enc).splitlines()
            break
        except UnicodeDecodeError:
            continue
    return parse_leaf_groups(lines)


def collect_cilin_relation_tuples(
    char_to_id: Dict[str, int],
    cilin_path: Path,
    *,
    source: str = "cilin",
    confidence: float = 0.85,
) -> List[RelationTuple]:
    if not cilin_path.is_file():
        return []
    out: List[RelationTuple] = []
    seen: set[tuple[int, int, str]] = set()
    for code, words in _read_cilin_leaf_groups(cilin_path):
        ids = [char_to_id[w] for w in words if w in char_to_id]
        if len(ids) < 2:
            continue
        gc = hierarchy_codes_json(code)
        for id_a, id_b in itertools.combinations(ids, 2):
            row = normalize_relation_tuple(
                id_a, id_b, "syn", confidence, source, gc,
            )
            if row is None:
                continue
            key = (row[0], row[1], row[2])
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out


def collect_flat_relation_tuples(
    char_to_id: Dict[str, int],
    flat_edges: Iterable[dict],
) -> List[RelationTuple]:
    out: List[RelationTuple] = []
    for e in flat_edges:
        head_id = char_to_id.get(e["head"])
        tail_id = char_to_id.get(e["tail"])
        if head_id is None or tail_id is None:
            continue
        row = normalize_relation_tuple(
            head_id,
            tail_id,
            e["relation_type"],
            float(e.get("confidence") or 0.5),
            str(e.get("source") or "unknown"),
            None,
        )
        if row is not None:
            out.append(row)
    return out


def collect_compound_ant_tuples(
    db: Session,
    char_to_id: Dict[str, int],
    compounds: Iterable[str],
    *,
    source: str = "compound_ant",
    confidence: float = 0.9,
) -> List[RelationTuple]:
    out: List[RelationTuple] = []
    seen_compounds: set[str] = set()
    for compound in compounds:
        if len(compound) != 2 or compound in seen_compounds:
            continue
        seen_compounds.add(compound)
        if not _compound_exists(db, compound):
            continue
        id_a = char_to_id.get(compound[0])
        id_b = char_to_id.get(compound[1])
        if not id_a or not id_b:
            continue
        row = normalize_relation_tuple(id_a, id_b, "ant", confidence, source, None)
        if row is not None:
            out.append(row)
    return out


def merge_relation_tuples(rows: Iterable[RelationTuple]) -> List[RelationTuple]:
    """Dedupe triples; keep lowest source rank when metadata differs."""
    bucket: Dict[tuple[int, int, str], RelationTuple] = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        prev = bucket.get(key)
        if prev is None:
            bucket[key] = row
            continue
        prev_rank = _SOURCE_RANK.get(prev[4] or "", 99)
        new_rank = _SOURCE_RANK.get(row[4] or "", 99)
        if new_rank < prev_rank:
            bucket[key] = row
        elif new_rank == prev_rank and row[5] and not prev[5]:
            bucket[key] = row
    return list(bucket.values())


def collect_static_relation_tuples(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    compound_path: Path | str | None = None,
) -> List[RelationTuple]:
    manifest = load_manifest(manifest_path or DEFAULT_MANIFEST)
    sources = select_sources(manifest, defaults_only=True)
    static_src = next((s for s in sources if s.get("parser") == "current_static"), None)
    if static_src is None:
        raise FileNotFoundError("current_static source not found in syn_ant manifest")

    paths = static_src.get("paths") or {}
    rank = int(static_src.get("source_rank") or 70)
    char_to_id = get_char_to_primary_id(db)

    cilin_rel = paths.get("cilin")
    cilin_path = (ROOT / cilin_rel) if cilin_rel else None
    if cilin_path is not None and not cilin_path.is_file():
        cilin_path = None

    port = StaticThesaurusPort(
        thesaurus_syn_path=str(ROOT / paths["thesaurus_syn"]) if paths.get("thesaurus_syn") else None,
        thesaurus_ant_path=str(ROOT / paths["thesaurus_ant"]) if paths.get("thesaurus_ant") else None,
        auto_load=True,
    )
    raw_flat = collect_guotong_flat_edges(port, source_rank=rank)
    db_chars = load_db_char_set(db)
    flat_edges = merge_staging_edges(
        normalize_edges(raw_flat, db_chars=db_chars, allow_external=False)
    )

    compounds = load_compound_antonyms(compound_path or DEFAULT_COMPOUND_PATH)
    parts = [
        collect_cilin_relation_tuples(char_to_id, cilin_path) if cilin_path else [],
        collect_flat_relation_tuples(char_to_id, flat_edges),
        collect_compound_ant_tuples(db, char_to_id, compounds),
    ]
    return merge_relation_tuples(itertools.chain.from_iterable(parts))


def build_word_relations(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    compound_path: Path | str | None = None,
    replace_static: bool = True,
) -> dict[str, Any]:
    """Collect static syn/ant rows in memory, then one bulk insert."""
    t0 = time.perf_counter()
    stats: dict[str, Any] = {"cleared": 0, "candidates": 0, "inserted": 0}

    if replace_static:
        for source_id in (*STATIC_SOURCES, *LEGACY_SOURCES):
            stats["cleared"] += clear_word_relations_source(db, source_id)

    rows = collect_static_relation_tuples(
        db,
        manifest_path=manifest_path,
        compound_path=compound_path,
    )
    stats["candidates"] = len(rows)
    ins = insert_relation_records(db, rows)
    stats["inserted"] = ins["attempted"]
    stats["chunks"] = ins["chunks"]
    stats["elapsed_s"] = round(time.perf_counter() - t0, 3)
    return stats


__all__ = [
    "build_word_relations",
    "collect_cilin_relation_tuples",
    "collect_guotong_flat_edges",
    "collect_static_relation_tuples",
    "merge_relation_tuples",
]
