"""Ingest smoke — build-word-relations + bridge 邊界。"""
from __future__ import annotations

import json
import unittest

from app.domain.relations.bulk_insert import bulk_insert_word_relations, normalize_relation_tuple
from app.models.word import Word, WordRelation
from ingest.word_relations_build import collect_cilin_relation_tuples, merge_relation_tuples

from tests.smoke.helpers import CILIN_SAMPLE, memory_sessionmaker


class IngestSmokeTests(unittest.TestCase):
    def test_merge_prefers_cilin_over_guotong(self):
        rows = merge_relation_tuples([
            (1, 2, "syn", 0.8, "guotong", None),
            (1, 2, "syn", 0.85, "cilin", '["A"]'),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "cilin")

    def test_build_word_relations_inserts_canonical_cilin_rows(self):
        if not CILIN_SAMPLE.is_file():
            self.skipTest("cilin sample missing")
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
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
            codes = json.loads(rel.group_codes)
            self.assertTrue(codes)

    def test_normalize_relation_tuple_sorts_ids(self):
        row = normalize_relation_tuple(5, 2, "syn", 0.8, "cilin", None)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row[:3], (2, 5, "syn"))


if __name__ == "__main__":
    unittest.main()
