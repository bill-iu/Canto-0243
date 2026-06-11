import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation, SynAntEdge
from app.services.syn_ant_service import search_syn_ant
from ingest.syn_ant_merge import build_word_relations_from_staging, persist_staging_edges
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from ingest.syn_ant_sources import (
    parse_antonym_pairs,
    parse_cilin_like,
    parse_relation_pairs,
    parse_wordnet_synsets,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "syn_ant" / "fixtures"


class ParserTests(unittest.TestCase):
    def test_cilin_like_parser(self):
        edges = parse_cilin_like(FIXTURES / "cilin_sample.txt", "test_cilin")
        pairs = {(e["head"], e["tail"]) for e in edges if e["relation_type"] == "syn"}
        self.assertIn(("快樂", "愉快"), pairs)
        self.assertIn(("開心", "快樂"), pairs)

    def test_antonym_pairs_parser(self):
        edges = parse_antonym_pairs(FIXTURES / "antonym_sample.txt", "test_ant")
        pairs = {(e["head"], e["tail"]) for e in edges if e["relation_type"] == "ant"}
        self.assertIn(("快樂", "悲傷"), pairs)
        self.assertIn(("大", "細"), pairs)
        self.assertIn(("細", "大"), pairs)

    def test_wordnet_synsets_parser(self):
        edges = parse_wordnet_synsets(FIXTURES / "cow_sample.txt", "cow")
        self.assertTrue(any(e["head"] == "快樂" and e["tail"] == "愉快" for e in edges))
        self.assertTrue(any(e["evidence"].get("synset") == "100-n" for e in edges))

    def test_relation_pairs_parser(self):
        edges = parse_relation_pairs(FIXTURES / "relations.tsv", "pairs")
        self.assertTrue(any(e["head"] == "前" and e["tail"] == "後" and e["relation_type"] == "ant" for e in edges))


class NormalizeMergeTests(unittest.TestCase):
    def test_normalize_filters_invalid_and_merges_sources(self):
        raw = [
            {"head": "快樂", "tail": "愉快", "relation_type": "syn", "source": "a", "confidence": 0.8, "source_rank": 50},
            {"head": "快樂", "tail": "愉快", "relation_type": "syn", "source": "b", "confidence": 0.6, "source_rank": 40},
            {"head": "x", "tail": "愉快", "relation_type": "syn", "source": "bad"},
        ]
        norm = normalize_edges(raw, db_chars={"快樂", "愉快"}, allow_external=False)
        self.assertEqual(len(norm), 1)
        merged = merge_staging_edges(norm + [
            {"head": "快樂", "tail": "愉快", "relation_type": "syn", "source": "b", "confidence": 0.6, "source_rank": 40,
             "evidence": {}, "license_tag": "b", "in_db_head": True, "in_db_tail": True},
        ])
        self.assertEqual(len(merged), 1)
        self.assertIn("+", merged[0]["source"])


class RuntimeServiceTests(unittest.TestCase):
    def test_bidirectional_and_scoring(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="悲傷", code="22", jyutping="bei1 soeng1", length=2),
            ])
            db.add_all([
                WordRelation(id=1, word_id=1, related_id=2, relation_type="syn", score=0.95, source="manual"),
                WordRelation(id=2, word_id=1, related_id=3, relation_type="ant", score=0.9, source="manual"),
            ])
            db.commit()

            res = search_syn_ant(db, "快樂", include_static=False)
            by_char = {r["char"]: r for r in res}
            self.assertEqual(by_char["愉快"]["relation"], "syn")
            self.assertEqual(by_char["悲傷"]["relation"], "ant")
            self.assertTrue(by_char["愉快"]["in_db"])

            # backward: query 愉快 should still find 快樂 as syn via related_id direction
            res2 = search_syn_ant(db, "愉快", include_static=False)
            chars2 = [r["char"] for r in res2 if r["relation"] == "syn"]
            self.assertIn("快樂", chars2)

    def test_staging_to_word_relations(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as db:
            db.add_all([
                Word(id=10, char="大", code="2", jyutping="daai6", length=1),
                Word(id=11, char="細", code="2", jyutping="sai3", length=1),
            ])
            db.commit()
            edges = normalize_edges(
                parse_antonym_pairs(FIXTURES / "antonym_sample.txt", "test_ant"),
                db_chars={"大", "細"},
                allow_external=False,
            )
            persist_staging_edges(db, edges)
            stats = build_word_relations_from_staging(db)
            self.assertGreater(stats["inserted"], 0)
            rels = db.query(WordRelation).all()
            self.assertTrue(any(r.relation_type == "ant" for r in rels))


class CantoneseFixtureTests(unittest.TestCase):
    """Smoke tests for common lyric lookup chars."""

    def test_common_chars_do_not_echo_query(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as db:
            for ch in ("快樂", "悲傷", "開心", "前", "後", "大", "細"):
                db.add(Word(char=ch, code="22", jyutping="", length=len(ch)))
            db.commit()
            for q in ("快樂", "大"):
                res = search_syn_ant(db, q)
                self.assertNotIn(q, [r["char"] for r in res])


if __name__ == "__main__":
    unittest.main()
