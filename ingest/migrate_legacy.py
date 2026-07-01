"""One-shot export from legacy lyrics.db into declarative SSOT sidecars."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export_bridge_snapshot(db_path: Path, out_path: Path) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from ingest.bridge_snapshot import write_bridge_snapshot

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    session = sessionmaker(bind=engine)()
    try:
        return write_bridge_snapshot(session, out_path)
    finally:
        session.close()


def export_manual_relations(db_path: Path, out_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT w.char, r.char, wr.relation_type
        FROM word_relations wr
        JOIN words w ON w.id = wr.word_id
        JOIN words r ON r.id = wr.related_id
        WHERE wr.source = 'manual'
        """
    ).fetchall()
    conn.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["seed_char", "opposite_char", "relation_type", "note"])
        for seed, opposite, rtype in rows:
            w.writerow([seed, opposite, rtype, ""])
    return len(rows)
