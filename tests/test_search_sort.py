"""Unified search result sorting (CONTEXT.md §搜尋結果排序)."""

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ESSAY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_ranking_sample.txt"
ESSAY_EMPTY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_empty.txt"
CURATED_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "fixtures" / "curated_sample.txt"


class EssaySortTierTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_rime_char_for_tests()

    def test_pure_han_before_mixed_literal(self):
        from app.lexicon.essay_index import load_essay_corpus
        from app.models.word import Word
        from app.services.essay_sort import sort_words

        load_essay_corpus(ESSAY_FIXTURE)
        words = [
            Word(char="A片", code="33", jyutping="e1 pin3", length=2),
            Word(char="先生", code="33", jyutping="sin1 saang1", length=2),
        ]
        ordered = [w.char for w in sort_words(words)]
        self.assertEqual(ordered[0], "先生")

    def test_essay_frequency_before_curated_when_freq_differs(self):
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus
        from app.models.word import Word
        from app.services.essay_sort import sort_words

        load_essay_corpus(ESSAY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        words = [
            Word(char="門童", code="20", jyutping="mun4 tung4", length=2),
            Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
        ]
        ordered = [w.char for w in sort_words(words)]
        self.assertEqual(ordered[0], "門童")
        self.assertEqual(ordered[1], "門前")

    def test_curated_breaks_tie_when_essay_equal(self):
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus, reset_essay_for_tests
        from app.models.word import Word
        from app.services.essay_sort import sort_words

        reset_essay_for_tests()
        load_essay_corpus(ESSAY_EMPTY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        words = [
            Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
            Word(char="門童", code="20", jyutping="mun4 tung4", length=2),
        ]
        ordered = [w.char for w in sort_words(words)]
        self.assertEqual(ordered[0], "門童")


class SearchSortIntegrationTests(unittest.TestCase):
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

    def test_pure_digit_search_sorts_by_unified_key(self):
        from app.models.word import Word
        from app.services.query_engine import search_words

        with self.Session() as db:
            db.add_all([
                Word(char="A片", code="33", jyutping="e1 pin3", length=2),
                Word(char="門前", code="33", jyutping="mun4 cin4", length=2),
                Word(char="門童", code="33", jyutping="mun4 tung4", length=2),
            ])
            db.commit()
            results = search_words(q="33", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars[0], "門童")
        self.assertLess(chars.index("門前"), chars.index("A片"))

    def test_mask_search_uses_same_sort_as_pure_digit(self):
        from app.models.word import Word
        from app.services.query_engine import search_words

        with self.Session() as db:
            db.add_all([
                Word(
                    char="門", code="2", jyutping="mun4",
                    finals='["un"]', initials='["m"]', length=1,
                ),
                Word(
                    char="門前", code="20", jyutping="mun4 cin4",
                    finals='["un","in"]', initials='["m","c"]', length=2,
                ),
                Word(
                    char="門童", code="20", jyutping="mun4 tung4",
                    finals='["un","ung"]', initials='["m","t"]', length=2,
                ),
            ])
            db.commit()
            results = search_words(q="門0", mode="m2", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars.index("門童"), 0)

    def test_equals_rhyme_search_sorts_by_essay_frequency(self):
        import json

        from app.models.word import Word
        from app.services.query_engine import search_words

        shared_finals = json.dumps(["oeng", "ong"])
        with self.Session() as db:
            db.add_all([
                Word(
                    char="香港", code="22", jyutping="hoeng1 gong2",
                    finals=shared_finals, initials='["h","g"]', length=2,
                ),
                Word(
                    char="香江", code="22", jyutping="hoeng1 gong1",
                    finals=shared_finals, initials='["h","g"]', length=2,
                ),
                Word(
                    char="香島", code="22", jyutping="hoeng1 dou2",
                    finals=json.dumps(["oeng", "ou"]), initials='["h","d"]', length=2,
                ),
            ])
            db.commit()
            results = search_words(q="香港=", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars[0], "香江")
        self.assertIn("香港", chars)
        self.assertNotIn("香島", chars)

    def test_jyutping_query_search_sorts_by_unified_key(self):
        from app.models.word import Word
        from app.services.query_engine import search_words

        with self.Session() as db:
            db.add_all([
                Word(char="門", code="0", jyutping="mun4", length=1),
                Word(char="問", code="3", jyutping="man6", length=1),
                Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
                Word(char="路數", code="24", jyutping="lou6 sou3", length=2),
            ])
            db.commit()
            results = search_words(q="mun4", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars, ["門"])


if __name__ == "__main__":
    unittest.main()
