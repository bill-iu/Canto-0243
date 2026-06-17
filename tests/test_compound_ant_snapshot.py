"""反義複合快照與 search_compound_ant 契約。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_ant import (
    TIER_CURATED,
    TIER_MORPHEME,
    TIER_SYNTHESIZED,
    build_compound_ant_snapshot,
    reset_compound_ant_snapshot_for_tests,
    search_compound_ant,
)
from app.models.word import Word, WordRelation


class CompoundAntSnapshotTests(unittest.TestCase):
    def setUp(self):
        reset_compound_ant_snapshot_for_tests()

    def tearDown(self):
        reset_compound_ant_snapshot_for_tests()

    def _session_with_seed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all([
            Word(id=1, char="生", code="3", jyutping="saang1", length=1),
            Word(id=2, char="死", code="3", jyutping="sei2", length=1),
            Word(id=3, char="是", code="3", jyutping="si6", length=1),
            Word(id=4, char="非", code="3", jyutping="fei1", length=1),
            Word(id=5, char="甲", code="3", jyutping="gaap3", length=1),
            Word(id=6, char="乙", code="3", jyutping="jat6", length=1),
            Word(id=10, char="生死", code="33", jyutping="saang1 sei2", length=2),
            Word(id=11, char="是非", code="33", jyutping="si6 fei1", length=2),
            Word(id=12, char="甲乙", code="33", jyutping="gaap3 jat6", length=2),
            Word(id=13, char="散步", code="44", jyutping="saan3 bou6", length=2),
        ])
        session.add_all([
            WordRelation(word_id=1, related_id=2, relation_type="ant", source="test"),
            WordRelation(word_id=3, related_id=4, relation_type="ant", source="test"),
            WordRelation(word_id=5, related_id=6, relation_type="ant", source="test"),
        ])
        session.commit()
        return session

    def test_snapshot_covers_curated_and_morpheme(self):
        session = self._session_with_seed()
        try:
            snapshot = build_compound_ant_snapshot(session)
            self.assertIn("生死", snapshot.curated_literals)
            self.assertIn("是非", snapshot.curated_literals)
            self.assertIn("甲乙", snapshot.morpheme_literals)
            self.assertIn("甲乙", snapshot.snapshot_literals)
            self.assertNotIn("散步", snapshot.snapshot_literals)
        finally:
            session.close()

    def test_pair_symmetry_when_both_in_lexicon(self):
        session = self._session_with_seed()
        try:
            session.add(Word(id=14, char="乙甲", code="33", jyutping="jat6 gaap3", length=2))
            session.commit()
            snapshot = build_compound_ant_snapshot(session)
            self.assertIn("甲乙", snapshot.morpheme_literals)
            self.assertIn("乙甲", snapshot.morpheme_literals)
        finally:
            session.close()

    def test_morpheme_scan_in_snapshot_not_synthesized_tier(self):
        session = self._session_with_seed()
        try:
            session.add(Word(id=7, char="樂", code="3", jyutping="lok6", length=1))
            session.add(Word(id=8, char="悲", code="3", jyutping="bei1", length=1))
            session.add(Word(id=15, char="樂悲", code="33", jyutping="lok6 bei1", length=2))
            session.add(
                WordRelation(word_id=7, related_id=8, relation_type="ant", source="test")
            )
            session.commit()
            snapshot = build_compound_ant_snapshot(session)
            tiers = search_compound_ant(session, k=12)
            self.assertIn("樂悲", snapshot.morpheme_literals)
            self.assertEqual(tiers.get("樂悲"), TIER_MORPHEME)
        finally:
            session.close()

    def test_search_compound_ant_tier_order(self):
        session = self._session_with_seed()
        try:
            with patch(
                "app.domain.relations.compound_ant.load_compound_antonyms",
                return_value=["生死"],
            ):
                reset_compound_ant_snapshot_for_tests()
                tiers = search_compound_ant(session, k=12)
            self.assertEqual(tiers["生死"], TIER_CURATED)
            self.assertEqual(tiers["是非"], TIER_MORPHEME)
            self.assertEqual(tiers["甲乙"], TIER_MORPHEME)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
