import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation, SynAntEdge
from app.domain.relations.pool import PoolSnapshot, build_pool
from app.domain.relations.ranking import (
    final_score as _final_score,
    should_include_synonym as _should_include_synonym,
    sort_ant_pool as _sort_ant_pool,
    sort_syn_pool as _sort_syn_pool,
)
from app.services.relation_syntax_executor import RelationSyntaxExecutor
from app.services.relation_search import (
    search_syn_ant,
    search_relation_chars,
)
from ingest.bridge_pool_context import IngestBridgePoolContext
from ingest.compound_antonyms import ingest_compound_ant_char_pairs
from ingest.syn_ant_merge import (
    build_word_relations_from_staging,
    ingest_cilin_leaf_direct,
    persist_staging_edges,
    expand_antonyms_via_cilin_synonyms,
    expand_antonyms_via_embedding_syn_bridge,
    expand_antonyms_via_syn_endpoints,
    collect_ant_mirror_char_pairs,
)
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from ingest.cilin_leaf import (
    groups_to_syn_edges,
    is_cilin_leaf_code,
    leaf_code_to_hierarchy_codes,
    parse_leaf_group_line,
    parse_leaf_groups,
)
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

    def test_leaf_code_to_hierarchy_codes(self):
        self.assertEqual(
            leaf_code_to_hierarchy_codes("Aa01A01="),
            ["A", "Aa", "Aa01", "Aa01A", "Aa01A01="],
        )
        self.assertEqual(
            leaf_code_to_hierarchy_codes("Ca01B01="),
            ["C", "Ca", "Ca01", "Ca01B", "Ca01B01="],
        )

    def test_cilin_edges_carry_full_group_codes(self):
        groups = [("Aa01A01=", ["快樂", "愉快", "開心"])]
        edges = groups_to_syn_edges(groups, "cilin")
        self.assertEqual(len(edges), 3)
        for e in edges:
            self.assertEqual(
                e["evidence"]["group_codes"],
                ["A", "Aa", "Aa01", "Aa01A", "Aa01A01="],
            )

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

    def test_ant_ranking_prioritizes_same_length_and_priority_list(self):
        morphemes = {"悲", "傷", "苦", "難"}
        pool = [
            {"char": "悲", "relation": "ant", "_sort": 32.0, "source": "antisem"},
            {"char": "悲傷", "relation": "ant", "_sort": 32.0, "source": "antisem"},
            {"char": "傷心", "relation": "ant", "_sort": 32.0, "source": "ant_cilin_exanded"},
            {"char": "難過", "relation": "ant", "_sort": 32.0, "source": "ant_cilin_exanded"},
            {"char": "悲悲慘慘", "relation": "ant", "_sort": 32.0, "source": "ant_cilin_exanded"},
        ]
        ranked = _sort_ant_pool("快樂", pool, morphemes)
        chars = [x["char"] for x in ranked]
        self.assertNotIn("悲", chars)
        self.assertEqual(chars[:3], ["悲傷", "傷心", "難過"])

    def test_ant_ranking_helper_excludes_single_char_for_two_char_query(self):
        self.assertFalse(_should_include_synonym("快樂", "悲"))
        self.assertTrue(_should_include_synonym("快樂", "悲傷"))

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

    def test_syn_ant_pagination(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as db:
            words = [Word(id=i + 1, char=f"詞{i}", code="22", jyutping="", length=2) for i in range(20)]
            db.add(Word(id=100, char="快樂", code="22", jyutping="", length=2))
            db.add_all(words)
            for i, w in enumerate(words):
                db.add(WordRelation(
                    word_id=100,
                    related_id=w.id,
                    relation_type="syn",
                    score=0.9,
                    source="test",
                ))
            db.commit()

            page1 = search_syn_ant(db, "快樂", limit=5, offset=0, include_static=False)
            page2 = search_syn_ant(db, "快樂", limit=5, offset=5, include_static=False)
            self.assertEqual(len(page1), 5)
            self.assertEqual(len(page2), 5)
            self.assertTrue(set(r["char"] for r in page1).isdisjoint(r["char"] for r in page2))
            all_pages = search_syn_ant(db, "快樂", limit=100, offset=0, include_static=False)
            self.assertEqual(len(all_pages), 20)

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

            rel = db.query(WordRelation).filter(WordRelation.relation_type == "syn").first()
            self.assertIsNotNone(rel.group_codes)
            import json
            codes = json.loads(rel.group_codes)
            self.assertEqual(codes, ["A", "Aa", "Aa01", "Aa01A", "Aa01A01="])

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


class AntCilinExpansionTests(unittest.TestCase):
    def _seed_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session

    def test_expand_antonyms_via_cilin_synonyms(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
                Word(id=4, char="難過", code="22", jyutping="", length=2),
                Word(id=5, char="愉快", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", score=0.9, source="antisem"))
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.85, source="cilin"),
                WordRelation(word_id=2, related_id=4, relation_type="syn", score=0.85, source="cilin"),
                WordRelation(word_id=1, related_id=5, relation_type="syn", score=0.85, source="cilin"),
            ])
            db.commit()

            stats = expand_antonyms_via_cilin_synonyms(db, source="ant_cilin_exanded")
            self.assertGreater(stats["inserted"], 0)

            derived = (
                db.query(WordRelation)
                .filter(WordRelation.source == "ant_cilin_exanded", WordRelation.relation_type == "ant")
                .all()
            )
            pairs = {(r.word_id, r.related_id) for r in derived}
            self.assertIn((1, 3), pairs)  # 快樂 ant 傷心
            self.assertIn((1, 4), pairs)  # 快樂 ant 難過
            self.assertIn((2, 5), pairs)  # 悲傷 ant 愉快 (via 快樂 syn 愉快)
            self.assertNotIn((1, 1), pairs)

            res = search_syn_ant(db, "快樂", include_static=False)
            ant_chars = [r["char"] for r in res if r["relation"] == "ant"]
            self.assertIn("悲傷", ant_chars)
            self.assertIn("傷心", ant_chars)
            self.assertIn("難過", ant_chars)

    def test_expand_skips_existing_ant_pairs(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="antisem"))
            db.add(WordRelation(word_id=1, related_id=3, relation_type="ant", source="manual"))
            db.add(WordRelation(word_id=2, related_id=3, relation_type="syn", source="cilin"))
            db.commit()

            stats = expand_antonyms_via_cilin_synonyms(db, source="ant_cilin_exanded")
            self.assertEqual(stats["inserted"], 0)
            self.assertGreater(stats["skipped_existing"], 0)

    def test_expand_idempotent_with_replace_source(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="antisem"))
            db.add(WordRelation(word_id=2, related_id=3, relation_type="syn", source="cilin"))
            db.commit()

            stats1 = expand_antonyms_via_cilin_synonyms(db, source="ant_cilin_exanded")
            count1 = db.query(WordRelation).filter(WordRelation.source == "ant_cilin_exanded").count()
            stats2 = expand_antonyms_via_cilin_synonyms(db, source="ant_cilin_exanded", dedupe_existing=True)
            count2 = db.query(WordRelation).filter(WordRelation.source == "ant_cilin_exanded").count()
            self.assertEqual(count1, count2)
            self.assertGreater(stats1["inserted"], 0)
            self.assertEqual(stats2["inserted"], 0)


class AntSynBridgeExpansionTests(unittest.TestCase):
    def _seed_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session

    def test_expand_antonyms_via_embedding_syn_bridge(self):
        from unittest.mock import MagicMock, patch

        Session = self._seed_db()
        vectors = {
            "快樂": [1.0, 0.0],
            "開心": [0.99, 0.01],
            "悲傷": [0.0, 1.0],
        }

        def fake_encode(chars, model):
            return {c: vectors[c] for c in chars if c in vectors}

        with patch("ingest.syn_ant_merge._load_embedding_model", return_value=MagicMock()), patch(
            "ingest.syn_ant_merge._encode_char_batch", side_effect=fake_encode
        ):
            with Session() as db:
                db.add_all([
                    Word(id=1, char="快樂", code="22", jyutping="", length=2),
                    Word(id=2, char="開心", code="22", jyutping="", length=2),
                    Word(id=4, char="悲傷", code="22", jyutping="", length=2),
                ])
                db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="test"))
                db.add(WordRelation(word_id=2, related_id=4, relation_type="ant", score=0.9, source="antisem"))
                db.commit()

                stats = expand_antonyms_via_embedding_syn_bridge(
                    db, source="ant_syn_bridge", include_static=False
                )
                self.assertEqual(stats["targets"], 1)
                self.assertEqual(stats["bridged"], 1)
                self.assertEqual(stats["inserted"], 1)

                derived = (
                    db.query(WordRelation)
                    .filter(WordRelation.source == "ant_syn_bridge", WordRelation.relation_type == "ant")
                    .all()
                )
                self.assertEqual(len(derived), 1)
                self.assertEqual((derived[0].word_id, derived[0].related_id), (1, 4))
                self.assertAlmostEqual(derived[0].score, 0.9999, places=3)

                res = search_syn_ant(db, "快樂", include_static=False)
                ant_chars = [r["char"] for r in res if r["relation"] == "ant"]
                self.assertIn("悲傷", ant_chars)

    def test_expand_bridge_offset_limit_and_chunk_insert(self):
        from unittest.mock import MagicMock, patch

        Session = self._seed_db()
        vectors = {
            "甲": [1.0, 0.0],
            "乙": [0.99, 0.01],
            "丙": [0.0, 1.0],
            "丁": [1.0, 0.0],
            "戊": [0.99, 0.01],
            "己": [0.0, 1.0],
        }

        def fake_encode(chars, model):
            return {c: vectors[c] for c in chars if c in vectors}

        with patch("ingest.syn_ant_merge._load_embedding_model", return_value=MagicMock()), patch(
            "ingest.syn_ant_merge._encode_char_batch", side_effect=fake_encode
        ):
            with Session() as db:
                db.add_all([
                    Word(id=1, char="甲", code="2", jyutping="", length=1),
                    Word(id=2, char="乙", code="2", jyutping="", length=1),
                    Word(id=3, char="丙", code="2", jyutping="", length=1),
                    Word(id=4, char="丁", code="2", jyutping="", length=1),
                    Word(id=5, char="戊", code="2", jyutping="", length=1),
                    Word(id=6, char="己", code="2", jyutping="", length=1),
                ])
                db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="test"))
                db.add(WordRelation(word_id=2, related_id=3, relation_type="ant", score=0.9, source="antisem"))
                db.add(WordRelation(word_id=4, related_id=5, relation_type="syn", score=0.9, source="test"))
                db.add(WordRelation(word_id=5, related_id=6, relation_type="ant", score=0.9, source="antisem"))
                db.commit()

                batch_log: list[tuple[int, int, dict]] = []

                def on_batch(n, total, st, _next_offset=0):
                    batch_log.append((n, total, dict(st)))

                stats = expand_antonyms_via_embedding_syn_bridge(
                    db,
                    source="ant_syn_bridge",
                    include_static=False,
                    offset=0,
                    limit=1,
                    chunk_size=1,
                    on_batch=on_batch,
                )
                self.assertEqual(stats["total_targets"], 2)
                self.assertEqual(stats["offset"], 0)
                self.assertEqual(stats["targets"], 1)
                self.assertEqual(stats["batches"], 1)
                self.assertEqual(stats["bridged"], 1)
                self.assertEqual(stats["inserted"], 1)
                self.assertEqual(len(batch_log), 1)

                derived = (
                    db.query(WordRelation)
                    .filter(WordRelation.source == "ant_syn_bridge", WordRelation.relation_type == "ant")
                    .all()
                )
                self.assertEqual(len(derived), 1)
                # sorted targets: 丁 before 甲
                self.assertEqual((derived[0].word_id, derived[0].related_id), (4, 6))


class IngestBridgePoolContextTests(unittest.TestCase):
    def _seed_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session

    def _assert_pool_matches_ranker(self, db, query, *, include_static=False, thesaurus=None):
        pool_ctx = IngestBridgePoolContext(
            db, include_static=include_static, thesaurus=thesaurus
        )
        snapshot = build_pool(
            db,
            query,
            include_static=include_static,
            thesaurus=thesaurus,
            membership=pool_ctx._membership,
            quiet=True,
        )
        for kind in ("syn", "ant"):
            self.assertEqual(
                pool_ctx.relation_chars(query, kind),
                snapshot.chars(kind, expand=False),
                msg=f"{query!r} {kind}",
            )

    def test_relation_chars_matches_ranker_db_only(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="愉快", code="22", jyutping="", length=2),
                Word(id=4, char="悲傷", code="22", jyutping="", length=2),
                Word(id=5, char="傷心", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.95, source="cilin"),
                WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.80, source="test"),
                WordRelation(word_id=2, related_id=4, relation_type="ant", score=0.90, source="antisem"),
                WordRelation(word_id=2, related_id=5, relation_type="ant", score=0.70, source="ant_syn_bridge"),
            ])
            db.commit()

            self._assert_pool_matches_ranker(db, "快樂", include_static=False)
            self._assert_pool_matches_ranker(db, "開心", include_static=False)

    def test_relation_chars_matches_ranker_with_static_thesaurus(self):
        from unittest.mock import MagicMock

        thesaurus = MagicMock()
        thesaurus.get_synonyms.side_effect = lambda q: {
            "快樂": ["愉快", "高興"],
            "開心": ["欣喜"],
        }.get(q, [])
        thesaurus.get_antonyms.side_effect = lambda q: {
            "快樂": ["痛苦"],
            "開心": ["悲傷"],
        }.get(q, [])

        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="愉快", code="22", jyutping="", length=2),
                Word(id=4, char="悲傷", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="test"))
            db.commit()

            self._assert_pool_matches_ranker(
                db, "快樂", include_static=True, thesaurus=thesaurus
            )
            self._assert_pool_matches_ranker(
                db, "開心", include_static=True, thesaurus=thesaurus
            )

    def test_relation_chars_empty_query(self):
        Session = self._seed_db()
        with Session() as db:
            pool_ctx = IngestBridgePoolContext(db, include_static=False)
            self.assertEqual(pool_ctx.relation_chars("", "syn"), [])
            self.assertEqual(pool_ctx.relation_chars("   ", "ant"), [])
            self.assertEqual(pool_ctx.relation_chars("abc", "syn"), [])


class PoolSnapshotTests(unittest.TestCase):
    def test_ranked_pools_chars_syn_without_page(self):
        from unittest.mock import MagicMock

        pools = PoolSnapshot(
            query="快樂",
            syns=[
                {
                    "char": "開心",
                    "relation": "syn",
                    "source": "test",
                    "result_type": "syn",
                }
            ],
            ants=[{"char": "悲傷", "relation": "ant", "source": "test", "result_type": "syn"}],
            semantic=[],
            _db=MagicMock(),
            _thesaurus=MagicMock(),
            _include_static=False,
        )
        self.assertEqual(pools.chars("syn"), ["開心"])
        self.assertEqual(pools.chars("ant", expand=False), ["悲傷"])

    def test_search_relation_chars_matches_ranker_projection(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", source="test"))
            db.commit()
            ranked = build_pool(db, "快樂", include_static=False, quiet=True)
            via_adapter = search_relation_chars(db, "快樂", "syn", include_static=False)
            self.assertEqual(via_adapter, ranked.chars("syn", expand=False))


class RelationSyntaxExecutorTests(unittest.TestCase):
    def test_syn_mode_page_matches_search_syn_ant(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", source="test"))
            db.commit()
            from app.services.relation_search import search_syn_ant

            via_syn_ant = search_syn_ant(db, "快樂")
            via_executor = RelationSyntaxExecutor(db).syn_mode_page("快樂", limit=160, offset=0)
            self.assertEqual(via_executor, via_syn_ant)


class AntSynMirrorTests(unittest.TestCase):
    def _seed_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session

    def test_expand_antonyms_mirror_matches_tilde_endpoint(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="開心", code="33", jyutping="", length=2),
                Word(id=2, char="悲傷", code="33", jyutping="", length=2),
                Word(id=3, char="傷心", code="33", jyutping="", length=2),
                Word(id=4, char="難過", code="33", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="test"))
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", source="cilin"),
                WordRelation(word_id=2, related_id=4, relation_type="syn", source="cilin"),
            ])
            db.commit()

            stats = expand_antonyms_via_syn_endpoints(db, source="ant_syn_mirror", include_static=False)
            self.assertGreater(stats["inserted"], 0)

            bang_chars = search_relation_chars(
                db, "開心", "ant", include_static=False, expand_ant_via_syn=False,
            )
            tilde_endpoint = search_relation_chars(
                db, "悲傷", "syn", include_static=False, expand_ant_via_syn=False,
            )
            self.assertIn("悲傷", bang_chars)
            for ch in tilde_endpoint:
                self.assertIn(ch, bang_chars)
            self.assertIn("傷心", bang_chars)
            self.assertIn("難過", bang_chars)

    def test_collect_mirror_pairs_dedupes(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=10, char="你", code="2", jyutping="", length=1),
                Word(id=11, char="我", code="2", jyutping="", length=1),
                Word(id=12, char="吾", code="2", jyutping="", length=1),
            ])
            db.add(WordRelation(word_id=10, related_id=11, relation_type="ant", source="compound_ant"))
            db.add(WordRelation(word_id=11, related_id=12, relation_type="syn", source="cilin"))
            db.commit()

            pairs = collect_ant_mirror_char_pairs(db, include_static=False)
            self.assertIn(("你", "我"), pairs)
            self.assertIn(("你", "吾"), pairs)
            self.assertIn(("我", "你"), pairs)


class CompoundAntIngestTests(unittest.TestCase):
    def _seed_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_ingest_compound_ant_creates_char_pairs_for_db_compounds(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="生", code="3", jyutping="saang1", length=1),
                Word(id=2, char="死", code="3", jyutping="sei2", length=1),
                Word(id=3, char="動", code="4", jyutping="dung6", length=1),
                Word(id=4, char="靜", code="4", jyutping="zing6", length=1),
                Word(id=5, char="生死", code="33", jyutping="saang1 sei2", length=2),
                Word(id=6, char="動靜", code="44", jyutping="dung6 zing6", length=2),
            ])
            db.commit()

            stats = ingest_compound_ant_char_pairs(
                db,
                ["生死", "動靜", "甲乙"],
                source="compound_ant",
            )
            self.assertEqual(stats["matched_in_db"], 2)
            self.assertEqual(stats["inserted"], 2)
            self.assertEqual(stats["skipped_no_compound"], 1)

            rels = (
                db.query(WordRelation)
                .filter(WordRelation.source == "compound_ant", WordRelation.relation_type == "ant")
                .all()
            )
            pairs = {(r.word_id, r.related_id) for r in rels}
            self.assertIn((1, 2), pairs)
            self.assertIn((3, 4), pairs)

    def test_ingest_compound_ant_skips_existing_pairs(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="是", code="3", jyutping="si6", length=1),
                Word(id=2, char="非", code="3", jyutping="fei1", length=1),
                Word(id=3, char="是非", code="33", jyutping="si6 fei1", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="char_pair"))
            db.commit()

            stats = ingest_compound_ant_char_pairs(db, ["是非"], source="compound_ant")
            self.assertEqual(stats["matched_in_db"], 1)
            self.assertEqual(stats["inserted"], 0)
            self.assertEqual(stats["skipped_existing"], 1)

    def test_skips_missing_compounds_and_chars_no_word_inserts(self):
        Session = self._seed_db()
        with Session() as db:
            db.add_all([
                Word(id=1, char="生", code="3", jyutping="saang1", length=1),
                Word(id=2, char="死", code="3", jyutping="sei2", length=1),
                Word(id=3, char="生死", code="33", jyutping="saang1 sei2", length=2),
                Word(id=4, char="是", code="3", jyutping="si6", length=1),
                Word(id=5, char="是非", code="33", jyutping="si6 fei1", length=2),
            ])
            db.commit()
            word_count_before = db.query(Word).count()

            stats = ingest_compound_ant_char_pairs(
                db,
                ["生死", "愛憎", "是非"],
                dedupe_existing=False,
            )

            self.assertEqual(db.query(Word).count(), word_count_before)
            self.assertEqual(stats["matched_in_db"], 2)
            self.assertEqual(stats["skipped_no_compound"], 1)
            self.assertEqual(stats["skipped_no_char_id"], 1)
            self.assertEqual(stats["inserted"], 1)
            rel = (
                db.query(WordRelation)
                .filter(WordRelation.relation_type == "ant", WordRelation.source == "compound_ant")
                .one()
            )
            self.assertEqual((rel.word_id, rel.related_id), (1, 2))


class IngestLockTests(unittest.TestCase):
    def test_stale_lock_removed_when_pid_dead(self):
        import tempfile
        from ingest.ingest_lock import acquire_ingest_lock, IngestLockError

        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp)
            path = lock_dir / "test.lock"
            path.write_text("999999\n", encoding="utf-8")
            acquired = acquire_ingest_lock("test", lock_dir=lock_dir)
            self.assertEqual(acquired, path)
            self.assertEqual(acquired.read_text(encoding="utf-8").strip(), str(__import__("os").getpid()))

    def test_live_lock_blocks_second_acquire(self):
        import tempfile
        from unittest.mock import patch
        from ingest.ingest_lock import acquire_ingest_lock, IngestLockError

        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp)
            path = lock_dir / "test.lock"
            path.write_text("888888\n", encoding="utf-8")
            with patch("ingest.ingest_lock._pid_alive", return_value=True):
                with self.assertRaises(IngestLockError):
                    acquire_ingest_lock("test", lock_dir=lock_dir)


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
