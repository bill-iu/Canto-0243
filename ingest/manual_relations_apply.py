"""Apply 關係補錄清單 at end of build-db."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.manual_relation_service import create_creator_manual_relation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = ROOT / "data" / "relations" / "manual_relations.tsv"


def apply_manual_relations(db: Session, path: Path | str = DEFAULT_TSV) -> int:
    tsv = Path(path)
    if not tsv.is_file():
        return 0
    count = 0
    with tsv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            seed = (row.get("seed_char") or "").strip()
            opposite = (row.get("opposite_char") or "").strip()
            rtype = (row.get("relation_type") or "").strip().lower()
            if not seed or not opposite or rtype not in ("syn", "ant"):
                continue
            create_creator_manual_relation(
                db,
                seed_char=seed,
                opposite_char=opposite,
                relation_type=rtype,  # type: ignore[arg-type]
            )
            count += 1
    return count
