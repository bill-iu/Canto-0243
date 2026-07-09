"""ADR v1.0.7 I2: lexicon SQLite index policy (TDD T1/T2)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ingest.lexicon_indexes import (
    FORBIDDEN_LEXICON_INDEXES,
    REQUIRED_LEXICON_INDEXES,
    finalize_lexicon_indexes,
    list_user_indexes,
)

_POLLUTION_INDEXES = (
    ("idx_length_code", "CREATE INDEX idx_length_code ON words(length, code)"),
    ("idx_length_code_finals", "CREATE INDEX idx_length_code_finals ON words(length, code, finals)"),
    (
        "idx_length_code_finals_model",
        "CREATE INDEX idx_length_code_finals_model ON words(length, code, finals)",
    ),
    ("idx_words_length", "CREATE INDEX idx_words_length ON words(length)"),
    ("ix_words_length", "CREATE INDEX ix_words_length ON words(length)"),
    ("ix_words_code", "CREATE INDEX ix_words_code ON words(code)"),
    ("ix_words_finals", "CREATE INDEX ix_words_finals ON words(finals)"),
    ("ix_words_initials", "CREATE INDEX ix_words_initials ON words(initials)"),
    ("ix_words_char", "CREATE INDEX ix_words_char ON words(char)"),
    ("ix_word_relations_word_id", "CREATE INDEX ix_word_relations_word_id ON word_relations(word_id)"),
    ("ix_word_relations_related_id", "CREATE INDEX ix_word_relations_related_id ON word_relations(related_id)"),
    ("ix_word_relations_relation_type", "CREATE INDEX ix_word_relations_relation_type ON word_relations(relation_type)"),
    ("idx_word_rel_word_type", "CREATE INDEX idx_word_rel_word_type ON word_relations(word_id, relation_type)"),
    ("idx_word_rel_related_type", "CREATE INDEX idx_word_rel_related_type ON word_relations(related_id, relation_type)"),
)


def _seed_polluted_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE words (
              id INTEGER PRIMARY KEY,
              char VARCHAR(50),
              code VARCHAR(20),
              jyutping VARCHAR(100),
              length INTEGER,
              initials VARCHAR(200),
              finals VARCHAR(200),
              source_flags INTEGER
            );
            CREATE TABLE word_relations (
              id INTEGER PRIMARY KEY,
              word_id INTEGER NOT NULL,
              related_id INTEGER NOT NULL,
              relation_type VARCHAR(16) NOT NULL,
              score FLOAT,
              source VARCHAR(32),
              group_codes TEXT,
              UNIQUE(word_id, related_id, relation_type)
            );
            """
        )
        for _name, sql in _POLLUTION_INDEXES:
            conn.execute(sql)
        # ADR-0038: explicit UNIQUE on top of table CONSTRAINT (duplicate to drop)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_word_relation "
            "ON word_relations(word_id, related_id, relation_type)"
        )


class LexiconIndexPolicyTests(unittest.TestCase):
    def test_finalize_drops_forbidden_and_keeps_required(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            db_path = Path(fh.name)
        try:
            _seed_polluted_db(db_path)
            before = list_user_indexes(db_path)
            # uq is forbidden only when table already has UNIQUE constraint
            self.assertTrue((FORBIDDEN_LEXICON_INDEXES - {"uq_word_relation"}) & before)

            finalize_lexicon_indexes(db_path)

            after = list_user_indexes(db_path)
            self.assertFalse((FORBIDDEN_LEXICON_INDEXES - {"uq_word_relation"}) & after)
            self.assertTrue(REQUIRED_LEXICON_INDEXES <= after)
            # seed has table UNIQUE + explicit uq → explicit dropped
            self.assertNotIn("uq_word_relation", after)
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_finalize_drops_duplicate_uq_when_table_constraint(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            db_path = Path(fh.name)
        try:
            with sqlite3.connect(db_path) as conn:
                conn.executescript(
                    """
                    CREATE TABLE word_relations (
                      id INTEGER PRIMARY KEY,
                      word_id INTEGER NOT NULL,
                      related_id INTEGER NOT NULL,
                      relation_type VARCHAR(16) NOT NULL,
                      UNIQUE(word_id, related_id, relation_type)
                    );
                    CREATE UNIQUE INDEX uq_word_relation
                      ON word_relations(word_id, related_id, relation_type);
                    CREATE TABLE words (
                      id INTEGER PRIMARY KEY, char TEXT, code TEXT, length INTEGER,
                      initials TEXT, finals TEXT
                    );
                    CREATE INDEX ix_words_char ON words(char);
                    CREATE INDEX idx_length_code_finals ON words(length, code, finals);
                    CREATE INDEX idx_word_rel_word_type ON word_relations(word_id, relation_type);
                    CREATE INDEX idx_word_rel_related_type ON word_relations(related_id, relation_type);
                    """
                )
            dropped = finalize_lexicon_indexes(db_path)
            self.assertIn("uq_word_relation", dropped)
            self.assertNotIn("uq_word_relation", list_user_indexes(db_path))
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_explain_len_code_uses_composite_index(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            db_path = Path(fh.name)
        try:
            _seed_polluted_db(db_path)
            finalize_lexicon_indexes(db_path)
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    "INSERT INTO words(char,code,length,finals) VALUES('事業','346','2','[\"zi6\",\"jip6\"]')"
                )
                plan = conn.execute(
                    "EXPLAIN QUERY PLAN SELECT char FROM words WHERE length=2 AND code IN ('30','90')"
                ).fetchall()
            finally:
                conn.close()
            text = " ".join(str(cell) for row in plan for cell in row)
            self.assertIn("idx_length_code_finals", text)
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except PermissionError:
                pass


if __name__ == "__main__":
    unittest.main()