"""衍生反義快照 inject／烘焙（CONTEXT § 詞林衍生反義快照、§ 反義端點鏡射快照）。"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, aliased

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relations
from app.models.word import Word, WordRelation
from ingest.syn_ant_build import clear_word_relations_source
from app.domain.relations.cilin_derived import (
    CILIN_DERIVED_SOURCE,
    collect_lexicon_cilin_derived_pairs,
    write_cilin_derived_pairs_tsv,
)
from app.domain.thesaurus.port import default_thesaurus_port
from ingest.syn_ant_expand import (
    ANT_SYN_MIRROR_SOURCE,
    expand_antonyms_via_syn_endpoints,
)

ROOT = Path(__file__).resolve().parents[1]
MIRROR_SOURCE = ANT_SYN_MIRROR_SOURCE
DEFAULT_CILIN_SNAPSHOT = ROOT / "data" / "syn_ant" / "ant_cilin_exanded_pairs.tsv"
DEFAULT_MIRROR_SNAPSHOT = ROOT / "data" / "syn_ant" / "ant_syn_mirror_pairs.tsv"


def write_derived_ant_snapshot(
    db: Session,
    path: Path | str,
    *,
    source: str,
) -> int:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tail_word = aliased(Word)
    rows = (
        db.query(Word.char, tail_word.char, WordRelation.score)
        .join(WordRelation, WordRelation.word_id == Word.id)
        .join(tail_word, tail_word.id == WordRelation.related_id)
        .filter(
            WordRelation.source == source[:32],
            WordRelation.relation_type == "ant",
        )
        .all()
    )
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["head", "tail", "relation_type", "score"])
        for head, tail, score in rows:
            if not head or not tail or head == tail:
                continue
            w.writerow([head, tail, "ant", "" if score is None else f"{score:.6g}"])
    return len(rows)


def ingest_derived_ant_snapshot(
    db: Session,
    path: Path | str,
    *,
    source: str,
    replace: bool = True,
) -> dict:
    snap = Path(path)
    stats: dict[str, Any] = {"rows": 0, "inserted": 0, "skipped": 0, "cleared": 0, "missing": False}
    if not snap.is_file():
        stats["missing"] = True
        print(f"warning: derived ant snapshot missing: {snap}", file=sys.stderr)
        return stats

    if replace:
        stats["cleared"] = clear_word_relations_source(db, source[:32])

    char_to_id = get_char_to_primary_id(db)
    pending: list[WordRelation] = []
    for line in snap.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("head"):
            continue
        parts = re.split(r"[\t,]", line)
        if len(parts) < 3:
            continue
        head, tail, rtype = parts[0].strip(), parts[1].strip(), parts[2].strip().lower()
        if rtype != "ant" or not head or not tail or head == tail:
            continue
        stats["rows"] += 1
        head_id, tail_id = char_to_id.get(head), char_to_id.get(tail)
        if not head_id or not tail_id:
            stats["skipped"] += 1
            continue
        w, r = canonical_word_ids(head_id, tail_id)
        score = float(parts[3]) if len(parts) > 3 and parts[3].strip() else None
        pending.append(
            WordRelation(
                word_id=w,
                related_id=r,
                relation_type="ant",
                score=score,
                source=source[:32],
            )
        )
    if pending:
        stats["inserted"] = insert_relations(db, pending)
    return stats


def ingest_cilin_derived_ant_snapshot(
    db: Session,
    path: Path | str = DEFAULT_CILIN_SNAPSHOT,
) -> dict:
    return ingest_derived_ant_snapshot(db, path, source=CILIN_DERIVED_SOURCE)


def ingest_mirror_derived_ant_snapshot(
    db: Session,
    path: Path | str = DEFAULT_MIRROR_SNAPSHOT,
) -> dict:
    return ingest_derived_ant_snapshot(db, path, source=MIRROR_SOURCE)


def bake_derived_ant_snapshots(
    db: Session,
    *,
    cilin_path: Path | str = DEFAULT_CILIN_SNAPSHOT,
    mirror_path: Path | str = DEFAULT_MIRROR_SNAPSHOT,
    export_only: bool = False,
    cilin_syn_source: str = "cilin",
    cilin_confidence: float = 0.75,
    mirror_confidence: float = 0.72,
    include_static: bool = True,
    batch_size: int = 300,
) -> dict:
    stats: dict[str, Any] = {}

    if export_only:
        stats["cilin"] = {"exported": write_derived_ant_snapshot(db, cilin_path, source=CILIN_DERIVED_SOURCE)}
        stats["mirror"] = {"exported": write_derived_ant_snapshot(db, mirror_path, source=MIRROR_SOURCE)}
        return stats

    port = default_thesaurus_port()
    cilin_pairs = collect_lexicon_cilin_derived_pairs(db, port, include_static=include_static)
    cilin_exported = write_cilin_derived_pairs_tsv(
        cilin_path, cilin_pairs, confidence=cilin_confidence
    )
    stats["cilin"] = {"candidate_pairs": len(cilin_pairs), "exported": cilin_exported}

    clear_word_relations_source(db, MIRROR_SOURCE)
    mirror_expand = expand_antonyms_via_syn_endpoints(
        db,
        source=MIRROR_SOURCE,
        confidence=mirror_confidence,
        dedupe_existing=True,
        include_static=include_static,
        batch_size=batch_size,
    )
    mirror_exported = write_derived_ant_snapshot(db, mirror_path, source=MIRROR_SOURCE)
    stats["mirror"] = {"expand": mirror_expand, "exported": mirror_exported}
    return stats


__all__ = [
    "CILIN_DERIVED_SOURCE",
    "DEFAULT_CILIN_SNAPSHOT",
    "DEFAULT_MIRROR_SNAPSHOT",
    "MIRROR_SOURCE",
    "bake_derived_ant_snapshots",
    "ingest_cilin_derived_ant_snapshot",
    "ingest_derived_ant_snapshot",
    "ingest_mirror_derived_ant_snapshot",
    "write_derived_ant_snapshot",
]
