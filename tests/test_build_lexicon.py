"""build-db integration tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordSource
from ingest.lexicon_build import build_lexicon_words
from ingest.lexicon_truncate import truncate_lexicon_core

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MANIFEST = ROOT / "data" / "lexicon" / "fixtures" / "build_sources.yaml"


class BuildLexiconTests(unittest.TestCase):
    def test_build_lexicon_words_from_fixture_manifest(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        truncate_lexicon_core(session)
        n = build_lexicon_words(session, manifest_path=FIXTURE_MANIFEST)
        session.commit()
        self.assertGreater(n, 0)
        self.assertGreater(session.query(Word).filter(Word.char == "好").count(), 0)
        sources = session.query(WordSource).all()
        self.assertTrue(any(s.source == "rime" for s in sources))


if __name__ == "__main__":
    unittest.main()
