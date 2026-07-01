"""Lexicon build stats gate."""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from ingest.lexicon_stats import check_min_multi_char, lexicon_word_stats


class LexiconStatsTests(unittest.TestCase):
    def test_check_min_multi_char_raises_when_too_few(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add(Word(char="好", code="2", jyutping="hou2", length=1))
        session.commit()
        with self.assertRaises(ValueError):
            check_min_multi_char(session, 1)

    def test_lexicon_word_stats_counts_multi_char(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add_all([
            Word(char="好", code="2", jyutping="hou2", length=1),
            Word(char="開心", code="33", jyutping="hoi1 sam1", length=2),
        ])
        session.commit()
        stats = lexicon_word_stats(session)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["multi_char"], 1)
        check_min_multi_char(session, 1)


if __name__ == "__main__":
    unittest.main()
