"""Regression: compound_syn sort_key must work when word_cache returns dict rows."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.services.query_dispatch import search_words
from app.utils import word_cache


class CompoundSynWordCacheTest(unittest.TestCase):
    def setUp(self):
        word_cache.reset_word_cache_for_tests()

    def tearDown(self):
        word_cache.reset_word_cache_for_tests()

    def test_rhyme_anchor_with_warmed_word_cache(self):
        from app.domain.relations.compound_syn import reset_compound_syn_cache_for_tests

        reset_compound_syn_cache_for_tests()
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        try:
            with Session() as session:
                session.add_all([
                    Word(id=1, char="香", code="3", jyutping="hoeng1", finals='["oeng"]', length=1),
                    Word(id=2, char="港", code="3", jyutping="gong2", finals='["ong"]', length=1),
                    Word(id=3, char="海", code="3", jyutping="hoi2", finals='["oi"]', length=1),
                    Word(id=4, char="香港", code="33", jyutping="hoeng1 gong2", finals='["oeng","ong"]', length=2),
                    Word(id=5, char="海港", code="33", jyutping="hoi2 gong2", finals='["oi","ong"]', length=2),
                    Word(id=6, char="散步", code="44", jyutping="saan3 bou6", finals='["aan","ou"]', length=2),
                ])
                session.add_all([
                    WordRelation(word_id=1, related_id=2, relation_type="syn", source="test"),
                    WordRelation(word_id=3, related_id=2, relation_type="syn", source="test"),
                ])
                session.commit()

                rows = session.query(
                    Word.char,
                    Word.code,
                    Word.jyutping,
                    Word.finals,
                    Word.initials,
                    Word.length,
                ).all()
                word_cache.populate_word_cache_from_rows(rows)
                word_cache.complete_preload()
                self.assertTrue(word_cache.is_word_cache_ready())

                results = search_words(q="~~港", mode="m1", db=session, limit=50, offset=0)
                chars = [r["char"] for r in results]
                self.assertIn("香港", chars)
                self.assertIn("海港", chars)
                self.assertNotIn("散步", chars)
        finally:
            reset_compound_syn_cache_for_tests()


if __name__ == "__main__":
    unittest.main()
