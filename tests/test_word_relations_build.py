"""word_relations precompute: canonical triple + bulk insert."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.bulk_insert import normalize_relation_tuple
from app.models.word import Word, WordRelation
from ingest.word_relations_build import build_word_relations, merge_relation_tuples

ROOT = Path(__file__).resolve().parents[1]
CILIN_SAMPLE = ROOT / "data" / "syn_ant" / "fixtures" / "cilin_sample.txt"


class BulkInsertTests(unittest.TestCase):
    def test_normalize_relation_tuple_sorts_ids(self):
        row = normalize_relation_tuple(5, 2, "syn", 0.8, "cilin", None)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row[:3], (2, 5, "syn"))

    def test_merge_prefers_cilin_over_guotong(self):
        rows = merge_relation_tuples([
            (1, 2, "syn", 0.8, "guotong", None),
            (1, 2, "syn", 0.85, "cilin", '["A"]'),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "cilin")


class BuildWordRelationsTests(unittest.TestCase):
    def test_build_inserts_canonical_rows_with_group_codes(self):
        if not CILIN_SAMPLE.is_file():
            self.skipTest("cilin sample missing")
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
            from ingest.word_relations_build import collect_cilin_relation_tuples
            from app.domain.relations.bulk_insert import bulk_insert_word_relations

            rows = collect_cilin_relation_tuples(
                {"快樂": 1, "愉快": 2, "開心": 3},
                CILIN_SAMPLE,
            )
            self.assertGreater(len(rows), 0)
            stats = bulk_insert_word_relations(db, rows)
            self.assertEqual(stats["attempted"], len(rows))
            rel = db.query(WordRelation).filter(WordRelation.relation_type == "syn").first()
            self.assertIsNotNone(rel)
            self.assertLess(rel.word_id, rel.related_id)
            self.assertIsNotNone(rel.group_codes)
            codes = json.loads(rel.group_codes)
            self.assertTrue(codes)

    def test_chunked_insert_commits_per_chunk(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=i, char=f"字{i}", code="1", jyutping="zi6", length=1)
                for i in range(1, 6)
            ])
            db.commit()
            from app.domain.relations.bulk_insert import CHUNK_SIZE, RelationRecord, bulk_insert_word_relations

            records = [
                RelationRecord(1, i, "syn", 0.8, "test", None)
                for i in range(2, 6)
            ]
            # ponytail: force multiple chunks with tiny chunk_size
            stats = bulk_insert_word_relations(db, records, chunk_size=2)
            self.assertEqual(stats["attempted"], 4)
            self.assertEqual(stats["chunks"], 2)
            self.assertEqual(db.query(WordRelation).count(), 4)

    def test_conflict_drops_duplicate_without_error(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="2", jyutping="daai6", length=1),
                Word(id=2, char="細", code="2", jyutping="sai3", length=1),
            ])
            db.commit()
            from app.domain.relations.bulk_insert import RelationRecord, bulk_insert_word_relations

            dup = RelationRecord(1, 2, "ant", 0.9, "guotong", None)
            bulk_insert_word_relations(db, [dup, dup])
            self.assertEqual(db.query(WordRelation).count(), 1)

    def test_bulk_insert_path_fast_on_cilin_sample(self):
        if not CILIN_SAMPLE.is_file():
            self.skipTest("cilin sample missing")
        import time

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
            from ingest.word_relations_build import collect_cilin_relation_tuples
            from app.domain.relations.bulk_insert import bulk_insert_word_relations

            t0 = time.perf_counter()
            rows = collect_cilin_relation_tuples(
                {"快樂": 1, "愉快": 2, "開心": 3},
                CILIN_SAMPLE,
            )
            bulk_insert_word_relations(db, rows)
            elapsed = time.perf_counter() - t0
            self.assertGreater(len(rows), 0)
            self.assertLess(elapsed, 2.0)


if __name__ == "__main__":
    unittest.main()
