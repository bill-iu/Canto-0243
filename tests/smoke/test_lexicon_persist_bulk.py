"""C1/C2: single seal VACUUM; bulk persist matches overlay candidates."""
from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_build import (
    assert_persisted_matches_candidates,
    persist_lexicon_candidates,
)

_CLI = Path(__file__).resolve().parents[2] / "ingest" / "cli.py"


class LexiconPersistBulkTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
        self.Session = sessionmaker(bind=engine)
        self.engine = engine

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_persist_count_and_samples(self) -> None:
        candidates = [
            LexiconCandidate("香", "hoeng1", "1", ("rime",)),
            LexiconCandidate("香港", "hoeng1 gong2", "12", ("words_hk", "rime")),
            LexiconCandidate("詞", "ci4", "3", ("curated",)),
        ]
        with self.Session() as db:
            n = persist_lexicon_candidates(db, candidates)
            db.commit()
            self.assertEqual(n, 3)
            assert_persisted_matches_candidates(db, candidates)
            row = db.execute(
                text("SELECT length, source_flags FROM words WHERE char = :c"),
                {"c": "香港"},
            ).one()
            self.assertEqual(row[0], 2)
            self.assertEqual(row[1], 32 | 4)  # words_hk | rime

    def test_empty_persist(self) -> None:
        with self.Session() as db:
            self.assertEqual(persist_lexicon_candidates(db, []), 0)
            assert_persisted_matches_candidates(db, [])

    def test_build_db_seal_has_single_vacuum(self) -> None:
        src = _CLI.read_text(encoding="utf-8")
        self.assertEqual(src.count('conn.execute("VACUUM")'), 1)
        self.assertIn("_seal_lexicon_vacuum(REPO_ROOT", src)


if __name__ == "__main__":
    unittest.main()
