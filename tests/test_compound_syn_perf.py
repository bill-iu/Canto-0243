"""近義複合查詢效能行為 — 源 3 tier 快取與韻錨預縮。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_syn import (
    reset_compound_syn_snapshot_for_tests,
    search_compound_syn,
)
from app.models.word import Word, WordRelation
from app.services.query_dispatch import search_words
from app.utils import word_cache


class CompoundSynPerfTests(unittest.TestCase):
    def setUp(self):
        reset_compound_syn_snapshot_for_tests()
        word_cache.reset_word_cache_for_tests()

    def tearDown(self):
        reset_compound_syn_snapshot_for_tests()
        word_cache.reset_word_cache_for_tests()

    def test_search_compound_syn_reuses_session_tier_cache(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add(Word(id=1, char="朋友", code="33", jyutping="pang4 jau5", length=2))
        session.commit()
        try:
            with patch(
                "app.domain.relations.compound_syn.synthesize_compound_literals",
                return_value=set(),
            ) as mocked:
                first = search_compound_syn(session)
                second = search_compound_syn(session)
                self.assertEqual(first, second)
                mocked.assert_called_once()
        finally:
            session.close()

    def test_compound_syn_candidate_source_uses_word_cache_when_ready(self):
        from app.services.compound_syn_executor import CompoundSynCandidateSource

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all([
            Word(id=1, char="香港", code="33", jyutping="hoeng1 gong2", finals='["oeng","ong"]', length=2),
            Word(id=2, char="散步", code="44", jyutping="saan3 bou6", finals='["aan","ou"]', length=2),
        ])
        session.commit()
        try:
            rows = session.query(
                Word.char, Word.code, Word.jyutping, Word.finals, Word.initials, Word.length
            ).all()
            word_cache.populate_word_cache_from_rows(rows)
            word_cache.complete_preload()

            source = CompoundSynCandidateSource(session, frozenset({"香港"}))
            candidates, from_cache = source.get_candidates(2, mode="m1")
            self.assertTrue(from_cache)
            self.assertEqual([c["char"] for c in candidates], ["香港"])
        finally:
            session.close()

    def test_rhyme_query_still_correct_after_literal_narrowing(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all([
            Word(id=1, char="朋", code="3", jyutping="pang4", finals='["ang"]', length=1),
            Word(id=2, char="友", code="3", jyutping="jau5", finals='["au"]', length=1),
            Word(id=3, char="知", code="3", jyutping="zi1", finals='["i"]', length=1),
            Word(id=4, char="己", code="3", jyutping="gei2", finals='["ei"]', length=1),
            Word(id=5, char="你", code="2", jyutping="nei5", finals='["ei"]', length=1),
            Word(id=10, char="朋友", code="33", jyutping="pang4 jau5", finals='["ang","au"]', length=2),
            Word(id=11, char="知己", code="33", jyutping="zi1 gei2", finals='["i","ei"]', length=2),
        ])
        session.add(WordRelation(word_id=2, related_id=1, relation_type="syn", source="test"))
        session.add(WordRelation(word_id=3, related_id=4, relation_type="syn", source="test"))
        session.commit()
        try:
            rows = session.query(
                Word.char, Word.code, Word.jyutping, Word.finals, Word.initials, Word.length
            ).all()
            word_cache.populate_word_cache_from_rows(rows)
            word_cache.complete_preload()

            results = search_words(q="~~你", mode="m1", db=session, limit=50, offset=0)
            chars = [r["char"] for r in results]
            self.assertIn("知己", chars)
            self.assertNotIn("朋友", chars)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
