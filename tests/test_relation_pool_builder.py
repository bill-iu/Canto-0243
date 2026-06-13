"""Phase A: RelationPoolBuilder — single deep module for 近反義池建構."""

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.services.relation_pool_builder import RelationPoolBuilder
from app.services.relation_ranker import RelationRanker


class RelationPoolBuilderTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _seed_happy_sad(self, db):
        db.add_all([
            Word(id=1, char="快樂", code="22", jyutping="", length=2),
            Word(id=2, char="開心", code="22", jyutping="", length=2),
            Word(id=3, char="愉快", code="22", jyutping="", length=2),
            Word(id=4, char="悲傷", code="22", jyutping="", length=2),
        ])
        db.add_all([
            WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.95, source="cilin"),
            WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.80, source="test"),
            WordRelation(word_id=2, related_id=4, relation_type="ant", score=0.90, source="antisem"),
        ])
        db.commit()

    def test_syn_chars_match_relation_ranker(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            builder = RelationPoolBuilder(db)
            ranked = RelationRanker(db).rank("快樂", include_static=False, quiet=True)
            built = builder.build("快樂", include_static=False)

            self.assertEqual(built.chars("syn"), ranked.chars("syn", expand=False))
            self.assertEqual(built.chars("ant"), ranked.chars("ant", expand=False))

    def test_ingest_cached_membership_skips_full_table_scan_per_query(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            membership = {"快樂", "開心", "愉快", "悲傷"}
            builder = RelationPoolBuilder(db, membership=membership)

            with patch(
                "app.services.relation_pool_builder.chars_present_in_db",
                side_effect=AssertionError("ingest must use cached membership"),
            ):
                built = builder.build("快樂", include_static=False)

            self.assertEqual(built.chars("syn"), ["開心", "愉快"])


if __name__ == "__main__":
    unittest.main()
