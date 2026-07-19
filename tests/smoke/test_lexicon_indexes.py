"""ADR v1.0.7 I2 + measure-first P0: lexicon SQLite index policy."""
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

_REPO_DB = Path(__file__).resolve().parents[2] / "lyrics.db"

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


def _seed_minimal_words(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO words(char,code,length,finals,initials) VALUES"
        "('事業','346',2,'11','1.2'),"
        "('香港','39',2,'22','3.4'),"
        "('心','5',1,'5','6')"
    )
    conn.execute(
        "INSERT INTO word_relations(word_id, related_id, relation_type) VALUES (1, 2, 'syn')"
    )
    conn.commit()


def _plan_text(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> str:
    plan = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return " ".join(str(cell) for row in plan for cell in row)


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

    def test_finalize_creates_missing_required_indexes(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            db_path = Path(fh.name)
        try:
            with sqlite3.connect(db_path) as conn:
                conn.executescript(
                    """
                    CREATE TABLE words (
                      id INTEGER PRIMARY KEY, char TEXT, code TEXT, length INTEGER,
                      initials TEXT, finals TEXT
                    );
                    CREATE TABLE word_relations (
                      id INTEGER PRIMARY KEY,
                      word_id INTEGER NOT NULL,
                      related_id INTEGER NOT NULL,
                      relation_type VARCHAR(16) NOT NULL,
                      UNIQUE(word_id, related_id, relation_type)
                    );
                    """
                )
            finalize_lexicon_indexes(db_path)
            self.assertTrue(REQUIRED_LEXICON_INDEXES <= list_user_indexes(db_path))
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
            self.assertIn("idx_length_finals", list_user_indexes(db_path))
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_explain_golden_shapes_use_required_indexes(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            db_path = Path(fh.name)
        try:
            _seed_polluted_db(db_path)
            finalize_lexicon_indexes(db_path)
            conn = sqlite3.connect(db_path)
            try:
                _seed_minimal_words(conn)
                cases = (
                    (
                        "SELECT char FROM words WHERE length=2 AND code=?",
                        ("346",),
                        "idx_length_code_finals",
                    ),
                    (
                        "SELECT char FROM words WHERE length=2 AND code=? AND finals=?",
                        ("346", "11"),
                        "idx_length_code_finals",
                    ),
                    (
                        "SELECT char FROM words WHERE length=2 AND finals=?",
                        ("11",),
                        "idx_length_finals",
                    ),
                    (
                        "SELECT char FROM words WHERE char=?",
                        ("心",),
                        "ix_words_char",
                    ),
                    (
                        "SELECT related_id FROM word_relations "
                        "WHERE word_id=? AND relation_type=?",
                        (1, "syn"),
                        None,
                    ),
                )
                for sql, params, needle in cases:
                    text = _plan_text(conn, sql, params)
                    self.assertIn("SEARCH", text.upper(), msg=f"expected SEEK/SEARCH: {text}")
                    if needle:
                        self.assertIn(needle, text, msg=f"{sql} plan={text}")
                    else:
                        self.assertTrue(
                            "idx_word_rel" in text or "autoindex" in text.lower(),
                            msg=f"{sql} plan={text}",
                        )
            finally:
                conn.close()
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except PermissionError:
                pass

    @unittest.skipUnless(_REPO_DB.is_file(), "lyrics.db not present")
    def test_repo_lyrics_db_golden_explain_after_finalize(self):
        """Apply policy to a temp copy of SSOT; assert golden SEEK plans."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            copy_path = Path(fh.name)
        try:
            copy_path.write_bytes(_REPO_DB.read_bytes())
            finalize_lexicon_indexes(copy_path)
            self.assertTrue(REQUIRED_LEXICON_INDEXES <= list_user_indexes(copy_path))
            conn = sqlite3.connect(f"file:{copy_path.as_posix()}?mode=ro", uri=True)
            try:
                sample = conn.execute(
                    "SELECT length, code, finals, char FROM words "
                    "WHERE length=2 AND finals IS NOT NULL AND finals != '' LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(sample)
                length, code, finals, char = sample
                wid = conn.execute("SELECT word_id FROM word_relations LIMIT 1").fetchone()
                self.assertIsNotNone(wid)
                checks = (
                    (
                        "SELECT id FROM words WHERE length=? AND code=? LIMIT 10",
                        (length, code),
                        "idx_length_code_finals",
                    ),
                    (
                        "SELECT id FROM words WHERE length=? AND code=? AND finals=? LIMIT 10",
                        (length, code, finals),
                        "idx_length_code_finals",
                    ),
                    (
                        "SELECT id FROM words WHERE length=? AND finals=? LIMIT 10",
                        (length, finals),
                        "idx_length_finals",
                    ),
                    (
                        "SELECT id FROM words WHERE char=? LIMIT 10",
                        (char,),
                        "ix_words_char",
                    ),
                    (
                        "SELECT related_id FROM word_relations "
                        "WHERE word_id=? AND relation_type='syn' LIMIT 10",
                        (wid[0],),
                        None,  # autoindex or idx_word_rel_word_type
                    ),
                )
                for sql, params, needle in checks:
                    text = _plan_text(conn, sql, params)
                    self.assertIn("SEARCH", text.upper(), msg=f"{sql} plan={text}")
                    if needle:
                        self.assertIn(needle, text, msg=f"{sql} plan={text}")
                    else:
                        self.assertTrue(
                            "idx_word_rel" in text or "autoindex" in text.lower(),
                            msg=f"{sql} plan={text}",
                        )
            finally:
                conn.close()
        finally:
            try:
                copy_path.unlink(missing_ok=True)
            except PermissionError:
                pass


if __name__ == "__main__":
    unittest.main()
