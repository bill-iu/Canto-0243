from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import tuple_

from app.models.word import Word, WordRelation, SynAntEdge


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


def persist_staging_edges(db: Session, edges: Iterable[dict], *, clear: bool = True) -> int:
    if clear:
        db.query(SynAntEdge).delete()
    count = 0
    for e in edges:
        db.add(SynAntEdge(
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
        count += 1
    db.commit()
    return count


def build_word_relations_from_staging(
    db: Session,
    *,
    allow_external: bool = False,
    char_to_ids: Optional[Dict[str, List[int]]] = None,
) -> dict:
    char_to_ids = char_to_ids or get_char_to_ids(db)
    rows = db.query(SynAntEdge).all()
    stats = {"staging": len(rows), "inserted": 0, "skipped_no_id": 0, "skipped_external": 0}

    pending: List[dict] = []
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
                pending.append({
                    "word_id": wid,
                    "related_id": rid,
                    "relation_type": row.relation_type,
                    "score": row.confidence,
                    "source": (row.source or "")[:32],
                })

    if not pending:
        return stats

    dedup = {}
    for rel in pending:
        key = (rel["word_id"], rel["related_id"], rel["relation_type"])
        dedup[key] = rel

    keys = list(dedup.keys())
    existing = set()
    if keys:
        existing = set(
            db.query(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type)
            .filter(tuple_(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type).in_(keys))
            .all()
        )

    to_insert = [WordRelation(**dedup[k]) for k in dedup if k not in existing]
    db.add_all(to_insert)
    db.commit()
    stats["inserted"] = len(to_insert)
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
