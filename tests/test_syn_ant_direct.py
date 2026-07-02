"""關係直寫（CONTEXT § 關係直寫）— 唔經 syn_ant_edges staging。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from ingest.syn_ant_direct import ingest_flat_char_edges, ingest_static_relations

ROOT = Path(__file__).resolve().parents[1]
CILIN_SAMPLE = ROOT / "data" / "syn_ant" / "fixtures" / "cilin_sample.txt"
FIXTURES = ROOT / "tests" / "fixtures" / "syn_ant"


class IngestFlatCharEdgesTests(unittest.TestCase):
    def test_uses_primary_anchor_only(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=1, char="好", code="2", jyutping="hou2", length=1),
                Word(id=2, char="好", code="3", jyutping="hou3", length=1),
                Word(id=3, char="心", code="1", jyutping="sam1", length=1),
            ])
            db.commit()
            stats = ingest_flat_char_edges(
                db,
                [{
                    "head": "好",
                    "tail": "心",
                    "relation_type": "syn",
                    "source": "guotong",
                    "confidence": 0.8,
                }],
                char_to_id={"好": 1, "心": 3},
            )
            self.assertEqual(stats["inserted"], 1)
            rel = db.query(WordRelation).one()
            self.assertEqual({rel.word_id, rel.related_id}, {1, 3})

    def test_flat_batch_dedupes_within_chunk(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="2", jyutping="daai6", length=1),
                Word(id=2, char="細", code="2", jyutping="sai3", length=1),
            ])
            db.commit()
            edge = {
                "head": "大",
                "tail": "細",
                "relation_type": "ant",
                "source": "guotong",
                "confidence": 0.85,
            }
            stats = ingest_flat_char_edges(db, [edge, edge], char_to_id={"大": 1, "細": 2})
            self.assertEqual(stats["inserted"], 1)
            self.assertEqual(db.query(WordRelation).count(), 1)


class IngestStaticRelationsTests(unittest.TestCase):
    def _session_with_words(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        return Session, engine

    def test_cilin_leaf_writes_group_codes(self):
        if not CILIN_SAMPLE.is_file():
            self.skipTest("cilin sample missing")
        Session, _ = self._session_with_words()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
            # ponytail: point manifest cilin at sample via env override in direct call
            from ingest.syn_ant_direct import ingest_cilin_and_flat_static
            stats = ingest_cilin_and_flat_static(
                db,
                cilin_path=CILIN_SAMPLE,
                flat_edges=[],
                chunk_size=50,
            )
            self.assertGreater(stats["cilin"]["inserted"], 0)
            rel = db.query(WordRelation).filter(WordRelation.relation_type == "syn").first()
            self.assertIsNotNone(rel.group_codes)
            codes = json.loads(rel.group_codes)
            self.assertTrue(codes)

    def test_cilin_cross_chunk_dedupes(self):
        if not CILIN_SAMPLE.is_file():
            self.skipTest("cilin sample missing")
        Session, _ = self._session_with_words()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
            from ingest.syn_ant_build import ingest_cilin_leaf_direct
            stats = ingest_cilin_leaf_direct(db, CILIN_SAMPLE, chunk_size=1, dedupe_existing=True)
            self.assertGreater(stats["inserted"], 0)
            count = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
            stats2 = ingest_cilin_leaf_direct(db, CILIN_SAMPLE, chunk_size=1, dedupe_existing=True)
            self.assertEqual(stats2["inserted"], 0)
            self.assertEqual(db.query(WordRelation).filter(WordRelation.relation_type == "syn").count(), count)

    def test_no_syn_ant_edges_table_required(self):
        Session, engine = self._session_with_words()
        with Session() as db:
            db.add(Word(id=1, char="大", code="2", jyutping="daai6", length=1))
            db.add(Word(id=2, char="細", code="2", jyutping="sai3", length=1))
            db.commit()
            from ingest.syn_ant_direct import ingest_cilin_and_flat_static
            ingest_cilin_and_flat_static(
                db,
                cilin_path=None,
                flat_edges=[{
                    "head": "大",
                    "tail": "細",
                    "relation_type": "ant",
                    "source": "guotong",
                    "confidence": 0.85,
                }],
            )
            self.assertEqual(db.query(WordRelation).count(), 1)
        tables = inspect(engine).get_table_names()
        self.assertNotIn("syn_ant_edges", tables)


if __name__ == "__main__":
    unittest.main()
