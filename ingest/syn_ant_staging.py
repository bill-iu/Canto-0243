"""syn_ant_edges staging — normalize 管線 persist + report。"""

from __future__ import annotations

import json
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.word import SynAntEdge

INSERT_BATCH = 300

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

__all__ = ["INSERT_BATCH", "persist_staging_edges", "staging_report"]
