#!/usr/bin/env python3
"""
Backfill empty Word.code from jyutping (0243 tone digits).
Delete rows that become exact duplicates of an existing (char, code, jyutping) row.

Usage:
  python scripts/backfill_empty_codes.py --dry-run
  python scripts/backfill_empty_codes.py
  python scripts/backfill_empty_codes.py --batch-size 500
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_

from app.database import SessionLocal
from app.models.word import Word, WordRelation
from ingest.relation_canonical import canonical_word_ids
from utils import get_0243_code

WordKey = Tuple[str, str, str]  # (char, code, jyutping)


def _word_key(char: Optional[str], code: Optional[str], jyutping: Optional[str]) -> WordKey:
    return (char or "", code or "", jyutping or "")


def _derive_code(jyutping: Optional[str]) -> Optional[str]:
    code = get_0243_code(jyutping or "")
    if not code or "?" in code:
        return None
    return code


def build_keeper_index(db) -> Dict[WordKey, int]:
    """Map (char, code, jyutping) -> smallest word id for rows that already have code."""
    index: Dict[WordKey, int] = {}
    q = (
        db.query(Word.id, Word.char, Word.code, Word.jyutping)
        .filter(Word.code.isnot(None), Word.code != "")
        .order_by(Word.id)
    )
    for wid, char, code, jyut in q.yield_per(5000):
        key = _word_key(char, code, jyut)
        index.setdefault(key, int(wid))
    return index


def loser_has_relations(db, word_id: int) -> bool:
    return (
        db.query(WordRelation.id)
        .filter(or_(WordRelation.word_id == word_id, WordRelation.related_id == word_id))
        .first()
        is not None
    )


def merge_word_id_into(db, loser_id: int, winner_id: int) -> int:
    """Re-point word_relations from loser to winner, then caller deletes loser."""
    if loser_id == winner_id:
        return 0
    rels = (
        db.query(WordRelation)
        .filter(or_(WordRelation.word_id == loser_id, WordRelation.related_id == loser_id))
        .all()
    )
    if not rels:
        return 0
    touched = 0
    for rel in rels:
        w = winner_id if rel.word_id == loser_id else int(rel.word_id)
        r = winner_id if rel.related_id == loser_id else int(rel.related_id)
        db.delete(rel)
        touched += 1
        if w == r:
            continue
        cw, cr = canonical_word_ids(w, r)
        exists = (
            db.query(WordRelation.id)
            .filter(
                WordRelation.word_id == cw,
                WordRelation.related_id == cr,
                WordRelation.relation_type == rel.relation_type,
            )
            .first()
        )
        if not exists:
            db.add(
                WordRelation(
                    word_id=cw,
                    related_id=cr,
                    relation_type=rel.relation_type,
                    score=rel.score,
                    source=rel.source,
                    group_codes=rel.group_codes,
                )
            )
    return touched


def backfill_empty_codes(
    db,
    *,
    dry_run: bool = False,
    batch_size: int = 500,
    limit: Optional[int] = None,
) -> dict:
    stats = {
        "empty_code_rows": 0,
        "updated_code": 0,
        "deleted_duplicate": 0,
        "deleted_no_relations": 0,
        "deleted_with_relations": 0,
        "relations_remapped": 0,
        "skipped_no_jyutping": 0,
        "skipped_no_derived_code": 0,
        "dry_run": dry_run,
    }

    keeper_index = build_keeper_index(db)
    empty_q = (
        db.query(Word.id, Word.char, Word.jyutping)
        .filter(or_(Word.code.is_(None), Word.code == ""))
        .order_by(Word.id)
    )
    if limit:
        empty_q = empty_q.limit(limit)

    to_update: List[Tuple[int, str]] = []
    to_delete_plain: List[int] = []
    to_delete_merge: List[Tuple[int, int]] = []

    for wid, char, jyut in empty_q.yield_per(2000):
        stats["empty_code_rows"] += 1
        if not (jyut or "").strip():
            stats["skipped_no_jyutping"] += 1
            continue
        derived = _derive_code(jyut)
        if not derived:
            stats["skipped_no_derived_code"] += 1
            continue
        key = _word_key(char, derived, jyut)
        keeper = keeper_index.get(key)
        if keeper is not None and keeper != int(wid):
            if loser_has_relations(db, int(wid)):
                to_delete_merge.append((int(wid), keeper))
            else:
                to_delete_plain.append(int(wid))
            continue
        to_update.append((int(wid), derived))
        keeper_index[key] = int(wid)

    stats["deleted_duplicate"] = len(to_delete_plain) + len(to_delete_merge)

    if dry_run:
        stats["updated_code"] = len(to_update)
        stats["deleted_no_relations"] = len(to_delete_plain)
        stats["deleted_with_relations"] = len(to_delete_merge)
        return stats

    for i in range(0, len(to_update), batch_size):
        chunk = to_update[i : i + batch_size]
        for wid, code in chunk:
            db.query(Word).filter(Word.id == wid).update({"code": code}, synchronize_session=False)
        db.commit()
        stats["updated_code"] += len(chunk)
        if (i // batch_size) % 20 == 0 and i:
            print(f"  updated {stats['updated_code']} codes...", flush=True)

    for i in range(0, len(to_delete_plain), batch_size):
        chunk = to_delete_plain[i : i + batch_size]
        db.query(Word).filter(Word.id.in_(chunk)).delete(synchronize_session=False)
        db.commit()
        stats["deleted_no_relations"] += len(chunk)

    for loser_id, winner_id in to_delete_merge:
        stats["relations_remapped"] += merge_word_id_into(db, loser_id, winner_id)
        db.query(Word).filter(Word.id == loser_id).delete(synchronize_session=False)
        stats["deleted_with_relations"] += 1
        if stats["deleted_with_relations"] % batch_size == 0:
            db.commit()
            print(f"  merged+deleted {stats['deleted_with_relations']} rows with relations...", flush=True)
    db.commit()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill empty Word.code from jyutping; drop exact duplicates.")
    parser.add_argument("--dry-run", action="store_true", help="Report stats only; no DB writes")
    parser.add_argument("--batch-size", type=int, default=500, help="Commit batch size")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N empty-code rows (debug)")
    args = parser.parse_args()

    print("Building keeper index and scanning empty-code rows...")
    with SessionLocal() as db:
        stats = backfill_empty_codes(
            db,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            limit=args.limit,
        )
    print("backfill-empty-codes stats:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
