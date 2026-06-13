"""近反義池 — build_pool + PoolSnapshot."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.pool import build_pool
from app.models.word import Word, WordRelation


class RelationPoolTests(unittest.TestCase):
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

    def test_build_pool_syn_and_ant_chars(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            snapshot = build_pool(db, "快樂", include_static=False, quiet=True)

            self.assertEqual(snapshot.chars("syn"), ["開心", "愉快"])
            self.assertEqual(snapshot.chars("ant"), [])

    def test_ingest_cached_membership_skips_full_table_scan_per_query(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            membership = {"快樂", "開心", "愉快", "悲傷"}

            with patch(
                "app.domain.relations.pool.chars_present_in_db",
                side_effect=AssertionError("ingest must use cached membership"),
            ):
                snapshot = build_pool(
                    db, "快樂", include_static=False, membership=membership, quiet=True
                )

            self.assertEqual(snapshot.chars("syn"), ["開心", "愉快"])


if __name__ == "__main__":
    unittest.main()
