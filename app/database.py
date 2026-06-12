"""Backward-compatible facade for database layer.

New code should import from ``app.db.connection``, ``app.db.bootstrap``,
or ``app.db.dialect`` directly.
"""

from app.db.bootstrap import (
    bootstrap_local_db,
    ensure_embedding_column,
    ensure_length_column,
    ensure_syn_ant_edges_table,
    ensure_word_relations_canonical_unique,
    ensure_word_relations_group_codes_column,
    ensure_word_relations_pair_unique,
    ensure_word_relations_table,
    start_length_backfill,
)
from app.db.connection import (
    DATABASE_URL,
    ENV,
    IS_POSTGRES,
    PROJECT_ROOT,
    Base,
    SessionLocal,
    engine,
    resolve_sqlite_database_url,
)
from app.db.dialect import contains_substring

__all__ = [
    "DATABASE_URL",
    "ENV",
    "IS_POSTGRES",
    "PROJECT_ROOT",
    "Base",
    "SessionLocal",
    "bootstrap_local_db",
    "contains_substring",
    "engine",
    "ensure_embedding_column",
    "ensure_length_column",
    "ensure_syn_ant_edges_table",
    "ensure_word_relations_canonical_unique",
    "ensure_word_relations_group_codes_column",
    "ensure_word_relations_pair_unique",
    "ensure_word_relations_table",
    "resolve_sqlite_database_url",
    "start_length_backfill",
]
