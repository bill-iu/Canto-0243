"""近義複合快照與 search_compound_syn 契約。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_syn import (
    TIER_CURATED,
    TIER_MORPHEME,
    TIER_SYNTHESIZED,
    build_compound_syn_snapshot,
    reset_compound_syn_snapshot_for_tests,
    search_compound_syn,
)
from app.models.word import Word, WordRelation


class CompoundSynSnapshotTests(unittest.TestCase):
    def setUp(self):
        reset_compound_syn_snapshot_for_tests()

    def tearDown(self):
        reset_compound_syn_snapshot_for_tests()

    def _session_with_seed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all([
            Word(id=1, char="朋", code="3", jyutping="pang4", length=1),
            Word(id=2, char="友", code="3", jyutping="jau5", length=1),
            Word(id=3, char="同", code="3", jyutping="tung4", length=1),
            Word(id=4, char="伴", code="3", jyutping="bun6", length=1),
            Word(id=5, char="海", code="3", jyutping="hoi2", length=1),
            Word(id=6, char="港", code="3", jyutping="gong2", length=1),
            Word(id=10, char="朋友", code="33", jyutping="pang4 jau5", length=2),
            Word(id=11, char="同伴", code="33", jyutping="tung4 bun6", length=2),
            Word(id=12, char="海港", code="33", jyutping="hoi2 gong2", length=2),
            Word(id=13, char="散步", code="44", jyutping="saan3 bou6", length=2),
        ])
        session.add_all([
            WordRelation(word_id=2, related_id=1, relation_type="syn", source="test"),
            WordRelation(word_id=3, related_id=4, relation_type="syn", source="test"),
            WordRelation(word_id=5, related_id=6, relation_type="syn", source="test"),
        ])
        session.commit()
        return session

    def test_snapshot_covers_curated_and_morpheme_only(self):
        session = self._session_with_seed()
        try:
            snapshot = build_compound_syn_snapshot(session)
            self.assertIn("朋友", snapshot.curated_literals)
            self.assertIn("同伴", snapshot.morpheme_literals)
            self.assertIn("朋友", snapshot.snapshot_literals)
            self.assertIn("同伴", snapshot.snapshot_literals)
            self.assertNotIn("散步", snapshot.snapshot_literals)
        finally:
            session.close()

    def test_snapshot_excludes_query_time_synthesis(self):
        session = self._session_with_seed()
        try:
            session.add(
                WordRelation(word_id=5, related_id=6, relation_type="ant", source="test")
            )
            session.commit()
            snapshot = build_compound_syn_snapshot(session)
            tiers = search_compound_syn(session, k=12)
            self.assertNotIn("海港", snapshot.snapshot_literals)
            self.assertEqual(tiers.get("海港"), TIER_SYNTHESIZED)
        finally:
            session.close()

    def test_search_compound_syn_tier_order(self):
        session = self._session_with_seed()
        try:
            tiers = search_compound_syn(session, k=12)
            self.assertEqual(tiers.get("朋友"), TIER_CURATED)
            self.assertEqual(tiers.get("同伴"), TIER_MORPHEME)
        finally:
            session.close()

    @patch("app.domain.relations.compound_syn.narrow_compound_syn_literals")
    def test_search_compound_syn_rhyme_char_narrows_literals(self, mock_narrow):
        session = self._session_with_seed()
        try:
            mock_narrow.return_value = frozenset({"海港"})
            tiers = search_compound_syn(session, k=12, rhyme_char="港")
            mock_narrow.assert_called_once()
            self.assertEqual(set(tiers.keys()), {"海港"})
            self.assertEqual(tiers["海港"], TIER_MORPHEME)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
