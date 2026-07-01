"""Ingest baked ant_syn_bridge snapshot (CONTEXT § 近義橋反義快照)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from sqlalchemy.orm import Session, aliased

from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relations
from app.models.word import Word, WordRelation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "data" / "syn_ant" / "ant_syn_bridge_pairs.tsv"
SOURCE = "ant_syn_bridge"


def write_bridge_snapshot(
    db: Session,
    path: Path | str,
    *,
    source: str = SOURCE,
) -> int:
    """Export ant_syn_bridge ant rows to a git-tracked TSV snapshot."""
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


def ingest_bridge_snapshot(
    db: Session,
    path: Path | str = DEFAULT_SNAPSHOT,
    *,
    source: str = SOURCE,
) -> dict:
    snap = Path(path)
    stats = {"rows": 0, "inserted": 0, "skipped": 0}
    if not snap.is_file():
        return stats
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
        wid, rid = char_to_id.get(head), char_to_id.get(tail)
        if not wid or not rid:
            stats["skipped"] += 1
            continue
        score = float(parts[3]) if len(parts) > 3 and parts[3].strip() else None
        pending.append(
            WordRelation(
                word_id=wid,
                related_id=rid,
                relation_type="ant",
                score=score,
                source=source[:32],
            )
        )
    if pending:
        stats["inserted"] = insert_relations(db, pending)
    return stats
