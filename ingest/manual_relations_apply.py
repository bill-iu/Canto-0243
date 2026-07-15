"""Apply 關係補錄清單 — build-db tail + 關係補錄熱套用."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session, aliased

from app.models.word import Word, WordRelation
from app.services.manual_relation_service import (
    MANUAL_ANT_MIRROR_SOURCE,
    MANUAL_SOURCE,
    MANUAL_SYN_CLUSTER_SOURCE,
    ManualRelationError,
    create_creator_manual_relation,
    expand_creator_manual_relation,
)
from ingest.syn_ant_build import clear_word_relations_source

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = ROOT / "data" / "relations" / "manual_relations.tsv"
TSV_HEADER = ("seed_char", "opposite_char", "relation_type", "note")

MANUAL_SOURCES = (MANUAL_SOURCE, MANUAL_SYN_CLUSTER_SOURCE, MANUAL_ANT_MIRROR_SOURCE)


def _undirected_manual_key(seed: str, opposite: str, rtype: str) -> tuple[str, str, str]:
    a, b = (seed, opposite) if seed <= opposite else (opposite, seed)
    return a, b, rtype


def merge_orphan_manual_directs_into_tsv(
    db: Session, path: Path | str = DEFAULT_TSV
) -> dict[str, int]:
    """Before wipe: append DB `source=manual` directs missing from the TSV.

    Cluster/mirror rows are ignored — hot-apply regenerates them from directs.
    """
    tsv = Path(path)
    existing: set[tuple[str, str, str]] = set()
    rows_out: list[list[str]] = []
    if tsv.is_file():
        with tsv.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            fieldnames = list(reader.fieldnames or TSV_HEADER)
            for row in reader:
                seed = (row.get("seed_char") or "").strip()
                opposite = (row.get("opposite_char") or "").strip()
                rtype = (row.get("relation_type") or "").strip().lower()
                note = (row.get("note") or "").strip()
                if not seed or not opposite or rtype not in ("syn", "ant"):
                    continue
                existing.add(_undirected_manual_key(seed, opposite, rtype))
                rows_out.append([seed, opposite, rtype, note])
    else:
        fieldnames = list(TSV_HEADER)

    w_seed = aliased(Word)
    w_opp = aliased(Word)
    db_rows = (
        db.query(w_seed.char, w_opp.char, WordRelation.relation_type)
        .join(w_seed, w_seed.id == WordRelation.word_id)
        .join(w_opp, w_opp.id == WordRelation.related_id)
        .filter(WordRelation.source == MANUAL_SOURCE)
        .filter(WordRelation.relation_type.in_(("syn", "ant")))
        .all()
    )
    merged = 0
    for seed, opposite, rtype in db_rows:
        seed_s = (seed or "").strip()
        opp_s = (opposite or "").strip()
        rtype_s = (rtype or "").strip().lower()
        if not seed_s or not opp_s or rtype_s not in ("syn", "ant"):
            continue
        key = _undirected_manual_key(seed_s, opp_s, rtype_s)
        if key in existing:
            continue
        existing.add(key)
        rows_out.append([seed_s, opp_s, rtype_s, "orphan-merge"])
        merged += 1

    if merged:
        tsv.parent.mkdir(parents=True, exist_ok=True)
        with tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(fieldnames[:4] if fieldnames else TSV_HEADER)
            writer.writerows(rows_out)

    return {"scanned": len(db_rows), "merged": merged, "tsv_rows": len(rows_out)}


def clear_manual_relation_sources(db: Session) -> int:
    """Remove all manual* rows so TSV is the sole manual authority."""
    total = 0
    for source in MANUAL_SOURCES:
        total += clear_word_relations_source(db, source)
    return total


def _iter_tsv_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            seed = (row.get("seed_char") or "").strip()
            opposite = (row.get("opposite_char") or "").strip()
            rtype = (row.get("relation_type") or "").strip().lower()
            if not seed or not opposite or rtype not in ("syn", "ant"):
                yield None
                continue
            yield seed, opposite, rtype


def apply_manual_relations(db: Session, path: Path | str = DEFAULT_TSV) -> dict[str, int]:
    """Apply TSV in two phases: directs first, then one-hop expand.

    Skips already_exists / not_in_lexicon (ponytail: partial lexicon / compound_ant).
    """
    tsv = Path(path)
    stats = {
        "applied": 0,
        "expanded": 0,
        "skipped_exists": 0,
        "skipped_other": 0,
        "errors": 0,
    }
    if not tsv.is_file():
        return stats

    rows: list[tuple[str, str, str]] = []
    for item in _iter_tsv_rows(tsv):
        if item is None:
            stats["skipped_other"] += 1
            continue
        rows.append(item)

    # Phase 1: direct edges only (avoid expand racing later TSV directs)
    for seed, opposite, rtype in rows:
        try:
            create_creator_manual_relation(
                db,
                seed_char=seed,
                opposite_char=opposite,
                relation_type=rtype,  # type: ignore[arg-type]
                expand=False,
            )
            stats["applied"] += 1
        except ManualRelationError as exc:
            if exc.code == "already_exists":
                stats["skipped_exists"] += 1
            else:
                stats["skipped_other"] += 1
        except Exception:
            stats["errors"] += 1
            db.rollback()

    # Phase 2: one-hop expansions for every TSV row that has a direct edge
    for seed, opposite, rtype in rows:
        try:
            expand_creator_manual_relation(
                db,
                seed_char=seed,
                opposite_char=opposite,
                relation_type=rtype,  # type: ignore[arg-type]
            )
            stats["expanded"] += 1
        except ManualRelationError:
            stats["skipped_other"] += 1
        except Exception:
            stats["errors"] += 1
            db.rollback()

    return stats


def hot_apply_manual_relations(
    db: Session, path: Path | str = DEFAULT_TSV
) -> dict[str, int]:
    """關係補錄熱套用：clear manual* then full TSV re-apply."""
    cleared = clear_manual_relation_sources(db)
    stats = apply_manual_relations(db, path)
    stats["cleared"] = cleared
    return stats


__all__ = [
    "DEFAULT_TSV",
    "MANUAL_SOURCES",
    "apply_manual_relations",
    "clear_manual_relation_sources",
    "hot_apply_manual_relations",
    "merge_orphan_manual_directs_into_tsv",
]
