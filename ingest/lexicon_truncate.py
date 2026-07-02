"""Truncate and rebuild lexicon tables."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


def truncate_lexicon_core(db: Session) -> None:
    existing = set(inspect(db.get_bind()).get_table_names())
    for table in ("word_sources", "word_relations", "syn_ant_edges", "words"):
        if table in existing:
            db.execute(text(f"DELETE FROM {table}"))
    db.commit()
