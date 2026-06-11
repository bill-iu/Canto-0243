import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation, SynAntEdge
from app.services.syn_ant_service import search_syn_ant, _should_include_synonym, _sort_syn_pool, _final_score
from ingest.syn_ant_merge import build_word_relations_from_staging, ingest_cilin_leaf_direct, persist_staging_edges
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from ingest.cilin_leaf import is_cilin_leaf_code, parse_leaf_group_line, parse_leaf_groups
from ingest.syn_ant_sources import (
    parse_antonym_pairs,
    parse_cilin_like,
    parse_cilin_lines,
    parse_relation_pairs,
    parse_wordnet_synsets,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "syn_ant" / "fixtures"


class ParserTests(unittest.TestCase):
    def test_cilin_leaf_code_pattern(self):
        self.assertTrue(is_cilin_leaf_code("Aa01A01="))
        self.assertTrue(is_cilin_leaf_code("Ca01B01="))
        self.assertFalse(is_cilin_leaf_code("A"))
        self.assertFalse(is_cilin_leaf_code("Aa"))
        self.assertFalse(is_cilin_leaf_code("Aa01"))
        self.assertFalse(is_cilin_leaf_code("Ca01B"))

    def test_cilin_leaf_parser_ignores_category_tags(self):
        lines = [
            "A 人",
            "Aa  人-泛称",
            "Aa01A01= 快樂 愉快 開心",
        ]
        groups = parse_leaf_groups(lines)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0], "Aa01A01=")
        self.assertEqual(groups[0][1], ["快樂", "愉快", "開心"])

    def test_cilin_like_parser(self):
        edges = parse_cilin_like(FIXTURES / "cilin_sample.txt", "test_cilin")
        pairs = {(e["head"], e["tail"]) for e in edges if e["relation_type"] == "syn"}
        self.assertIn(("快樂", "愉快"), pairs)
        self.assertIn(("快樂", "開心"), pairs)
        self.assertNotIn(("開心", "快樂"), pairs)  # canonical char order only
        self.assertEqual(len(edges), 6)  # 2 leaf groups x 3 pairs each

    def test_cilin_lines_no_bidirectional_duplicates(self):
        edges = parse_cilin_lines(["Aa01A01= 快樂 愉快 開心"], "cilin")
        self.assertEqual(len(edges), 3)
        heads_tails = {(e["head"], e["tail"]) for e in edges}
        self.assertNotIn(("愉快", "快樂"), heads_tails)

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
    def test_syn_ranking_filters_single_char_and_prioritizes_same_length(self):
        morphemes = {"快", "喜", "樂", "歡", "欣", "怡"}
        pool = [
            {"char": "快", "relation": "syn", "_sort": 32.0},
            {"char": "開心", "relation": "syn", "_sort": 32.0},
            {"char": "愉快", "relation": "syn", "_sort": 32.0},
            {"char": "喜歡", "relation": "syn", "_sort": 32.0},
            {"char": "高高興興", "relation": "syn", "_sort": 32.0},
        ]
        ranked = _sort_syn_pool("快樂", pool, morphemes)
        chars = [x["char"] for x in ranked]
        self.assertNotIn("快", chars)
        self.assertEqual(chars[:2], ["開心", "愉快"])

    def test_syn_ranking_helper_excludes_single_char_for_two_char_query(self):
        self.assertFalse(_should_include_synonym("快樂", "快"))
        self.assertTrue(_should_include_synonym("快樂", "開心"))

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

    def test_direct_cilin_ingest_dedupes(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        fixture = FIXTURES / "cilin_sample.txt"
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
                Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()
            stats1 = ingest_cilin_leaf_direct(db, fixture, dedupe_existing=True)
            self.assertGreater(stats1["inserted"], 0)
            count1 = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
            stats2 = ingest_cilin_leaf_direct(db, fixture, dedupe_existing=True)
            self.assertEqual(stats2["inserted"], 0)
            self.assertGreater(stats2["skipped_existing"], 0)
            count2 = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
            self.assertEqual(count1, count2)

            res = search_syn_ant(db, "愉快", include_static=False)
            self.assertIn("快樂", [r["char"] for r in res if r["relation"] == "syn"])

    def test_word_relation_triple_unique_and_canonical(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="2", jyutping="daai6", length=1),
                Word(id=2, char="細", code="2", jyutping="sai3", length=1),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="test"))
            db.commit()
            db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", source="test2"))
            db.commit()
            db.add(WordRelation(word_id=2, related_id=1, relation_type="syn", source="test3"))
            with self.assertRaises(Exception):
                db.commit()
            db.rollback()


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
