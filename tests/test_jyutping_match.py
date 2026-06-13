import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.jyutping_match import (
    expected_word_length,
    is_jyutping_query,
    matches_jyutping_query,
    parse_jyutping_query,
)
from app.services.query_dispatch import JYUTPING_SYN_MODE_HINT, SearchContext, execute_search
from app.services.query_dispatch import search_words

ESSAY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_ranking_sample.txt"
CURATED_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "fixtures" / "curated_sample.txt"


class JyutpingMatchTests(unittest.TestCase):
    def test_parse_mixed_tone_query(self):
        syllables = parse_jyutping_query("nei5 hou")
        self.assertEqual(len(syllables), 2)
        self.assertEqual(syllables[0].letters, "nei")
        self.assertEqual(syllables[0].tone, 5)
        self.assertEqual(syllables[1].letters, "hou")
        self.assertIsNone(syllables[1].tone)

    def test_all_toned_exact_match(self):
        self.assertTrue(matches_jyutping_query("ming4 baak6", "ming4 baak6"))
        self.assertTrue(matches_jyutping_query("ming4 baak6", "Ming4 Baak6"))
        self.assertFalse(matches_jyutping_query("ming4 bak6", "ming4 baak6"))

    def test_no_tone_letter_match(self):
        self.assertTrue(matches_jyutping_query("syut3", "syut"))
        self.assertTrue(matches_jyutping_query("nei5 hou2", "nei hou"))
        self.assertTrue(matches_jyutping_query("nei5 hou3", "nei hou"))
        self.assertFalse(matches_jyutping_query("noi6 hou3", "nei hou"))

    def test_mixed_tone_match(self):
        self.assertTrue(matches_jyutping_query("nei5 hou2", "nei5 hou"))
        self.assertTrue(matches_jyutping_query("nei5 hou3", "nei5 hou"))
        self.assertFalse(matches_jyutping_query("nei1 hou2", "nei5 hou"))

    def test_single_toned_exact_not_prefix(self):
        self.assertTrue(matches_jyutping_query("mun4", "mun4"))
        self.assertFalse(matches_jyutping_query("mun4 cin4", "mun4"))

    def test_single_no_tone_length_one(self):
        self.assertEqual(expected_word_length("syut"), 1)
        self.assertEqual(expected_word_length("nei hou"), 2)

    def test_is_jyutping_query(self):
        self.assertTrue(is_jyutping_query("syut"))
        self.assertTrue(is_jyutping_query("nei5 hou"))
        self.assertFalse(is_jyutping_query("你好"))
        self.assertFalse(is_jyutping_query("23"))


class JyutpingSearchIntegrationTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus

        load_essay_corpus(ESSAY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.utils.word_cache import reset_word_cache_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_word_cache_for_tests()

    def test_syut_finds_single_char(self):
        from app.models.word import Word

        with self.Session() as db:
            db.add_all(
                [
                    Word(char="雪", code="3", jyutping="syut3", length=1),
                    Word(char="說", code="3", jyutping="syut3", length=1),
                    Word(char="血", code="3", jyutping="hyut3", length=1),
                    Word(char="下雪", code="33", jyutping="haa6 syut3", length=2),
                ]
            )
            db.commit()
            results = search_words(q="syut", mode="m1", db=db, limit=20, offset=0)
            chars = [r["char"] for r in results]
        self.assertIn("雪", chars)
        self.assertIn("說", chars)
        self.assertNotIn("血", chars)
        self.assertNotIn("下雪", chars)

    def test_nei_hou_finds_ni_hao(self):
        from app.models.word import Word

        with self.Session() as db:
            db.add_all(
                [
                    Word(char="你好", code="45", jyutping="nei5 hou2", length=2),
                    Word(char="你", code="4", jyutping="nei5", length=1),
                    Word(char="內耗", code="24", jyutping="noi6 hou3", length=2),
                ]
            )
            db.commit()
            results = search_words(q="nei hou", mode="m1", db=db, limit=20, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars, ["你好"])

    def test_ming4_baak6_exact_pronunciation(self):
        from app.models.word import Word

        with self.Session() as db:
            db.add_all(
                [
                    Word(char="明白", code="46", jyutping="ming4 baak6", length=2),
                    Word(char="明白", code="46", jyutping="ming4 bak1", length=2),
                ]
            )
            db.commit()
            results = search_words(q="ming4 baak6", mode="m1", db=db, limit=20, offset=0)
            jyuts = [r["jyutping"] for r in results]
        self.assertEqual(jyuts, ["ming4 baak6"])

    def test_multi_reading_rows_all_returned(self):
        from app.models.word import Word

        with self.Session() as db:
            db.add_all(
                [
                    Word(char="行", code="4", jyutping="hang4", length=1),
                    Word(char="行", code="6", jyutping="hang6", length=1),
                    Word(char="行", code="2", jyutping="haang4", length=1),
                ]
            )
            db.commit()
            results = search_words(q="hang4", mode="m1", db=db, limit=20, offset=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["jyutping"], "hang4")

    def test_syn_mode_blocks_jyutping_with_hint(self):
        with self.Session() as db:
            result = execute_search(
                SearchContext(
                    q="syut", code=None, char=None, mode="syn", limit=10, offset=0, db=db
                )
            )
        self.assertEqual(result.items, [])
        self.assertEqual(result.hint, JYUTPING_SYN_MODE_HINT)


if __name__ == "__main__":
    unittest.main()
