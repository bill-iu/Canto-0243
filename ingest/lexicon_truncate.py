"""Truncate and rebuild lexicon tables."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def truncate_lexicon_core(db: Session) -> None:
    for table in ("word_sources", "word_relations", "syn_ant_edges", "words"):
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()
